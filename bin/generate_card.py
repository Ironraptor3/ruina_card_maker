import argparse
import hashlib
import json
import os
import sys

import PIL
import PIL.ImageFont
import PIL.Image
import PIL.ImageDraw

from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.compression import Compression

# Constants
COLOR_TITLE = "#000000"
COLOR_DESC = "#ffffff"
COLOR_OFFENSE = "#ffb7ce"
COLOR_DEFENSE = "#a1e3ee"
COLOR_KEYWORD = "#efd521"

TITLE_TEXT_FONT = 'P22 Johnston Underground Regular.ttf'
TITLE_TEXT_SIZE = 40
DESC_TEXT_FONT = 'NotoSansDisplay-SemiCondensed.ttf'
DESC_TEXT_SIZE = 32
COST_TEXT_FONT = 'P22 Johnston Underground Regular'
COST_TEXT_SIZE = 146

TEXT_LEFT = 550
TEXT_UP = 100
TEXT_RIGHT = 950
#TEXT_DOWN

TITLE_ANGLE_DEG = 11
TITLE_CENTER_X = 250
TITLE_CENTER_Y = 200

PSD_NAME = 'lor_template.psd'
PSD_MD5 = '53ed4a18dbd596add12463898e6a95bd'

def init_data(parent_dir, file_path):
    path = os.path.join(parent_dir, file_path)
    with open(path, 'r') as path_fd:
        data = json.load(path_fd)
    data['dir'] = os.path.dirname(path)
    return data

def get_field(data, field, relative=False):
    if field in data:
        if relative:
            return os.path.join(data['dir'], data[field])
        return data[field]

    parent_data = data.get('parent_data', None)
    if parent_data is None:
        parent = data.get('parent', None)
        if parent is not None:
            parent_data = init_data(data['dir'], parent)

    if parent_data is not None:
        field_data = get_field(parent_data, field, relative)
        if field_data is not None and relative:
            field_data = os.path.join(os.path.dirname(data['parent']), field_data)
        data[field] = field_data
        return field_data

    return None

def get_layer(current_layer, name, partial=False):
    if not current_layer.is_group():
        return None

    for layer in current_layer:
        if (partial and name in layer.name) or layer.name == name:
            return layer
    return None

def edit_dice_number(dice_number, data):
    num_dice = len(get_field(data, 'dice'))

    found_num = None
    for dn in dice_number:
        if num_dice == int(dn.name.split()[0]):
            dn.visible = True
            found_num = dn
        else:
            dn.visible = False

    assert found_num is not None, 'Invalid number of dice on page: %d' % num_dice

    for i in range(num_dice):
        dice_layer_i = get_layer(found_num, str(i + 1), partial=True) # 1-based indexing in psd
        found_type = False
        search_type = get_field(data, 'dice')[i]['type'].lower()

        for dice_type in dice_layer_i:
            if search_type == dice_type.name.lower():
                found_type = True
                dice_type.visible = True
            else:
                dice_type.visible = False
        assert found_type, 'No such dice type: %s' % search_type

def edit_page_type(page_type, data):
    search = get_field(data, 'type').lower()
    found = False
    for t in page_type:
        if search == t.name.lower():
            found = True
            t.visible = True
        else:
            t.visible = False

    assert found, 'No such page type: %s' % search

def edit_page_cost(page_cost, data):
    # Make these invisible; handle later
    get_layer(page_cost, 'Cost Grit', partial=True).visible = False
    get_layer(page_cost, 'Cost').visible = False

def edit_page_rarity(page_rarity, data):
    found = False
    search = get_field(data, 'rarity').lower()

    for rarity in page_rarity:
        if search == rarity.name.lower():
            found = True
            rarity.visible = True
            edit_page_type(get_layer(rarity, 'Card Type'), data)
            edit_page_cost(get_layer(rarity, 'Irrelevant Stuff'), data)
        else:
            rarity.visible = False

    assert found, 'No such page rarity: %s' % search

def edit_page_base(psd, page_base, data):
    get_layer(page_base, 'Do Not Delete').visible = get_field(data, 'grit') # This is the grit
    sample_img_layer = get_layer(page_base, '176m2')
    sample_img_layer.visible = False # Remove default image

    bbox = sample_img_layer.bbox # TODO (Future); I don't like this bbox
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    art_path = get_field(data, 'art', relative=True)
    with PIL.Image.open(art_path) as art:

        if art.width != bbox_width or art.height != bbox_height:
            print('WARN: dimensions for %s does not fit ( is %dx%d, expected %dx%d );' % (art_path,
                    art.width,
                    art.height,
                    bbox_width,
                    bbox_height),
                    file=sys.stderr)

        # Always resize to fit width
        if art.width != bbox_width:
            art_ratio = (art.height ) / ( art.width )
            target_height =  int( bbox_width * art_ratio )

            art = art.resize( (bbox_width, target_height),
                    resample=PIL.Image.Resampling.LANCZOS )

        page_art = PixelLayer.frompil(
            pil_im=art,
            psd_file=psd,
            top=bbox[1], # Top
            left=bbox[0], # Left
            compression=Compression.RLE
        )

        page_base.insert(0, page_art) # Lowest in ordering

def edit_combat_page(psd, combat_page, data):
    # No need for notes
    get_layer(combat_page, 'Notes', partial=True).visible = False
    # Doing this ourselves in PIL
    get_layer(combat_page, 'Card Text & Dice Details').visible = False

    edit_dice_number(get_layer(combat_page, 'Number of Dice'), data)
    edit_page_rarity(get_layer(combat_page, 'Card Rarity'), data)
    edit_page_base(psd, get_layer(combat_page, 'Card Base', partial=True), data)

def edit_page_class(psd, data):
    # No support for abno pages yet
    get_layer(psd, 'Abnormality Pages').visible = False

    combat_page = get_layer(psd, 'Combat Pages')
    combat_page.visible = True
    edit_combat_page(psd, combat_page, data)

def add_title(img, data):
    # Strategy: Create a new image, draw text, rotate, draw over
    # Need to do it on another image to gain access to a rotate() function

    # To be safe, just create an image the size of the original
    text_layer = PIL.Image.new('RGBA', (img.width, img.height), color=(0,0,0,0))
    draw = PIL.ImageDraw.Draw(text_layer)
    font = PIL.ImageFont.truetype(TITLE_TEXT_FONT, TITLE_TEXT_SIZE)

    center = ( TITLE_CENTER_X, TITLE_CENTER_Y )
    draw.multiline_text( center,
            get_field(data, 'name'),
            font=font,
            anchor='ms',
            fill=COLOR_TITLE )
    text_layer = text_layer.rotate( TITLE_ANGLE_DEG,
            resample=PIL.Image.Resampling.BILINEAR,
            center=center )

    return PIL.Image.alpha_composite( img, text_layer )

def add_cost( img, data ):
    return img # TODO

def add_text( img, data ):
    return img # TODO

def main(data_path, output_path, asset_path):
    psd_path = os.path.join(asset_path, PSD_NAME)
    with open(psd_path, 'rb') as check_psd:
        check_md5 = hashlib.file_digest(check_psd, 'md5').hexdigest()
        assert check_md5 == PSD_MD5, \
                'MD5 sum for %s did not match expected (%s!=%s), wrong psd supplied!' % (psd_path,
                check_md5,
                PSD_MD5)
    psd = PSDImage.open(psd_path)
    data = init_data('', data_path)

    # Toggle layers
    edit_page_class(psd, data)

    # Force redraws the psd instead of grabbing from the cache / buf
    img = psd.composite(force=True)

    img = add_title(img, data)
    img = add_cost(img, data)
    img = add_text(img, data)

    img.save(output_path, format='PNG') # Finally, output to png

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('data_path', type=str, help='Path to data to create a card')
    parser.add_argument('output_path', type=str, help='Path to output (ought to be a png file)')
    parser.add_argument('-a', '--asset-path', type=str, default=None,
            help='Path to the assets folder. Defaults to ../assets (relative to this script)')
    args = parser.parse_args()

    # As stated in the help text, `<scriptdir>/../assets/`
    if args.asset_path is None:
        args.asset_path = os.path.join(
            os.path.dirname(sys.argv[0]),
            '..',
            'assets')

    return (args.data_path, args.output_path, args.asset_path)

if __name__ == '__main__':
    main(*get_args())

