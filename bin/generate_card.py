import argparse
import hashlib
import json
import os
import sys

import PIL
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.compression import Compression

# Constants
COLOR_TITLE = 0x000000
COLOR_DESC = 0xffffff
COLOR_OFFENSE = 0xffb7ce
COLOR_DEFENSE = 0xa1e3ee
COLOR_KEYWORD = 0xefd521

TITLE_TEXT_FONT = 'P22 Johnston Underground Regular'
TITLE_TEXT_SIZE = 40
DESC_TEXT_FONT = 'NotoSansDisplay-SemiCondensed'
DESC_TEXT_SIZE = 32
COST_TEXT_FONT = 'P22 Johnston Underground Regular'
COST_TEXT_SIZE = 146

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

    dn = None
    found = False
    for dn in dice_number:
        if num_dice == int(dn.name.split()[0]):
            found = True
            break

    for i in range(num_dice):
        dice_layer_i = get_layer(dn, str(i + 1), partial=True) # 1-based indexing in psd
        for dice_type in dice_layer_i:
            dice_type.visible = dice_type.name.lower() == get_field(data, 'dice')[i]['type'].lower()

def edit_page_type(page_type, data):
    for t in page_type:
        t.visible = get_field(data, 'type').lower() == t.name.lower()

def edit_page_cost(page_cost, data):
    # Make these invisible; handle later
    get_layer(page_cost, 'Cost Grit').visible = False
    get_layer(page_cost, 'Cost').visible = False

def edit_page_rarity(page_rarity, data):
    for rarity in page_rarity:
        if get_field(data, 'rarity') == rarity.name:
            rarity.visible = True
            edit_page_type(get_layer(page_rarity, 'Card Type'), data)
            edit_page_cost(get_layer(page_rarity, 'Irrelevant Stuff'), data)
        else:
            rarity.visible = False

def edit_page_base(page_base, data):
    get_layer(page_base, 'Do Not Delete').visible = get_field(data, 'grit') # This is the grit
    sample_img_layer = get_layer(page_base, '176m2')
    sample_img_layer.visible = False # Remove default image
    bbox = sample_img_layer.bbox

    with PIL.Image.open(get_field(data, 'art', relative=True)) as art:
        page_art = PixelLayer.frompil(
            pil_im=art,
            #psd_file=None,
            top=bbox[1], # Top
            left=bbox[0], # Left
            compression=Compression.RLE
        )
        page_base.append(page_art)

def edit_combat_page(combat_page, data):
    # No need for notes
    get_layer(combat_page, 'Notes', partial=True).visible = False
    # Doing this ourselves in PIL
    get_layer(combat_page, 'Card Text & Dice Details').visible = False

    edit_dice_number(get_layer(combat_page, 'Number of Dice'), data)
    edit_page_rarity(get_layer(combat_page, 'Card Rarity'), data)
    edit_page_base(get_layer(combat_page, 'Card Base', partial=True), data)

def edit_page_class(psd, data):
    # No support for abno pages yet
    get_layer(psd, 'Abnormality Pages').visible = False

    combat_page = get_layer(psd, 'Combat Pages')
    combat_page.visible = True
    edit_combat_page(combat_page, data)

def main(data_path, output_path, asset_path):
    psd_path = os.path.join(asset_path, PSD_NAME)
    with open(psd_path, 'rb') as check_psd:
        check_md5 = hashlib.file_digest(check_psd, 'md5').hexdigest()
        assert check_md5 == PSD_MD5, 'MD5 sum for %s did not match expected (%s!=%s), wrong psd supplied!' % (psd_path, check_md5, PSD_MD5)
    psd = PSDImage.open(psd_path)
    data = init_data('', data_path)

    edit_page_class(psd, data)
    # Force redraws the psd instead of grabbing from the cache / buf
    img = psd.composite(force=True)

    # TODO text

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

