import argparse
from enum import Enum
import hashlib
import json
from math import ceil
import os
import sys

import PIL
import PIL.ImageFont
import PIL.Image
import PIL.ImageDraw
import PIL.ImageOps

from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.compression import Compression

# Constants
COLOR_TITLE = "#000000"
COLOR_COST = COLOR_TITLE
COLOR_DESC = "#ffffff"
COLOR_OFFENSE = "#ffb7ce"
COLOR_DEFENSE = "#a1e3ee"
COLOR_KEYWORD = "#efd521"
COLORIZE_MIDPOINT = 127

TITLE_TEXT_FONT = 'P22 Johnston Underground Regular.ttf'
TITLE_TEXT_SIZE = 40
DESC_TEXT_FONT = 'NotoSansDisplay-SemiCondensed.ttf'
DESC_TEXT_SIZE = 32
COST_TEXT_FONT = 'P22 Johnston Underground Regular.ttf'
COST_TEXT_SIZE = 146

TEXT_LEFT = 550
TEXT_UP = 65
TEXT_RIGHT = 950
TEXT_SPACER = 15
DICE_SPACER = 10

TITLE_ANGLE_DEG = 11
TITLE_CENTER_X = 250
TITLE_CENTER_Y = 200

COST_X = 80
COST_Y = 39

MINI_UP = 20
MINI_LEFT = 20
MINI_RIGHT = 520
MINI_DOWN = 700

PSD_NAME = 'lor_template.psd'
PSD_MD5 = '53ed4a18dbd596add12463898e6a95bd'

def init_data(parent_dir, file_path):
    path = os.path.join(parent_dir, file_path)
    with open(path, 'r') as path_fd:
        data = json.load(path_fd)
    data['dir'] = os.path.dirname(path)
    return data

# Perhaps there could be a better interface for the additional paths...
def get_field(data, field, relative=False, additional_paths=[]):
    if field not in data:
        # Resolve parent
        parent_data = data.get('parent_data', None)
        if parent_data is None:
            parent = data.get('parent', None)
            if parent is not None:
                parent_data = init_data(data['dir'], parent)

        # If a parent exists, try to get data from it
        if parent_data is not None:
            field_data = get_field(parent_data, field, relative)
            if field_data is not None and relative:
                field_data = os.path.join(os.path.dirname(data['parent']), field_data)
            data[field] = field_data

    if field in data:
        result = data[field]
        while result is not None and additional_paths:
            result = result.get(additional_paths.pop(0), None)

        if result is not None and relative:
            return os.path.join(data['dir'], result)
        return result

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

    # Get the layer with the proper number of dice
    for dn in dice_number:
        if num_dice == int(dn.name.split()[0]):
            dn.visible = True
            found_num = dn
        else:
            dn.visible = False

    assert found_num is not None, 'Invalid number of dice on page: %d' % num_dice

    # Set the correct type for each of these dice
    for i in range(num_dice):
        dice_layer_i = get_layer(found_num, str(i + 1), partial=True) # 1-based indexing in psd
        found_type = False
        search_type = get_field(data, 'dice')[i]['type'].lower()

        for dice_type in dice_layer_i:
            if search_type == dice_type.name.lower().replace(' ', '_'):
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
    # Not recommended to be false at the moment if not using the `-m` option
    get_layer(page_base, 'Do Not Delete').visible = get_field(data, 'grit') is not False # This is the grit

    sample_img_layer = get_layer(page_base, '176m2')
    sample_img_layer.visible = False # Remove default image

    bbox = sample_img_layer.bbox
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    art_path = get_field(data, 'art', relative=True)
    with PIL.Image.open(art_path) as art:
        # Always resize to fit width
        #NOTE Could check to see if the ratio is about equal, then scale it in a different way (TODO?)
        if art.width != bbox_width:
            art_ratio = art.height / art.width
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

    # Slightly rotate the text to fix the banner
    text_layer = text_layer.rotate( TITLE_ANGLE_DEG,
            resample=PIL.Image.Resampling.BILINEAR,
            center=center )

    return PIL.Image.alpha_composite( img, text_layer )

def add_cost( asset_path, img, data ):
    draw = PIL.ImageDraw.Draw( img )
    font = PIL.ImageFont.truetype( COST_TEXT_FONT, COST_TEXT_SIZE )

    cost_grit_path, cost_grit_stroke_fill = {
            'paperback' : ('cost_grit_paperback.png', '#9FE195'),
            'hardcover' : ('cost_grit_hardcover.png', '#9FC3EF'),
            'limited' : ('cost_grit_limited.png', '#B78BE5'),
            "objet d'art" : ('cost_grit_objet.png', '#FFCB69'),
            'e.g.o' : ('cost_grit_ego.png', '#FFFFDB'),
            }[get_field(data, 'rarity').lower()]

    cost_grit_path = os.path.join( asset_path, 'cost_grit', cost_grit_path )
            
    draw.text( (COST_X, COST_Y),
        str(get_field(data, 'cost')),
        font=font,
        fill=COLOR_COST,
        stroke_width=5,
        stroke_fill=cost_grit_stroke_fill )

    if get_field( data, 'grit' ) is not False:
        img.alpha_composite( PIL.Image.open(cost_grit_path).convert('RGBA') ) 

    return img

class KeywordData(Enum):
    REGULAR = 0
    SPECIAL = 1
    IMAGE = 2
    BREAK = 3

def get_keywords( text, keyword_data ):
    '''
    Gets an array of regular text interwoven with keywords + metadata

    @param text the text to get keywords from
    @param keyword_data a dictionary object obtained from an `init_data` call
    @return An array with tuple objects, where the first element is a `KeywordData` enum.
    This contextualizes the other elements of the tuple.
    For ease, all text is broken up by splitting on whitespace (to enable word wrapping later)
    '''
    result = []
    while True:
        start = text.find('{')
        end = text.find('}')

        # No more keywords, the rest is plain text
        if start < 0 or end < 0:
            if len(text) != 0:
                result += [ (KeywordData.REGULAR, word + ' ') for word in text.split() ]
            return result
        else:
            # Keyword found

            # Append the text before as plain text
            if start > 0:
                result += [ (KeywordData.REGULAR, word + ' ') for word in text[:start].split() ]

            kw = text[start + 1:end]
            kw_data = get_field( keyword_data, kw )
            assert kw_data is not None, 'The keyword "%s" was not found in the keyword dictionary!' % kw

            if 'image' in kw_data:
                kw_img = PIL.Image.open( get_field(keyword_data,
                        kw,
                        relative=True,
                        additional_paths=['image', 'path']) )
                kw_cc = kw_data['image'].get( 'convert_color', False )
                result.append( (KeywordData.IMAGE, kw_img, kw_cc) )

            if 'text' in kw_data:
                text_content = kw_data['text']['content']
                text_color = kw_data['text'].get('color', None)
                result += [ (KeywordData.SPECIAL, word + ' ', text_color)
                        for word in text_content.split() ]

                # Kind of hacky- needed for certain special keywords e.g. summation
                if text_content.endswith('\n'):
                    result += [ (KeywordData.BREAK,) ]
            text = text[end + 1:]

def draw_keywords( keywords, draw, font, img=None, position=(0,0), default_color=COLOR_DESC, query_width=True ):
    '''
    Draws (or tests the drawing of) a keyword array, returned by `get_keywords`

    @param keywords an array of keywords, returned by `get_keywords`
    @param draw a PIL.ImageDraw instance
    @param font the font to draw in
    @param img Optional (mandatory if `query_width` is False) the image to draw on
    @param position Optional (mandatory if `query_width` is False) the offset to draw on the image
    @param default_color Optional (mandatory if `query_width` is False) the default color of the text and color converted images
    @param query_width Optional. If True (default), returns the width in pixels that this function requires. If False, actually draws.
    '''
    width = 0
    font_ascent, font_descent = font.getmetrics()

    for kw in keywords:
        kw_type = kw[0]
        if kw_type == KeywordData.BREAK:
            continue
        if kw_type == KeywordData.IMAGE:
            data_img, data_cc = kw[1:]
            if not query_width:
                if data_cc:
                    mask = data_img.getchannel('A')
                    data_img = PIL.ImageOps.grayscale(data_img)
                    data_img = PIL.ImageOps.colorize(data_img,
                            black='black',
                            mid=default_color,
                            white='white',
                            midpoint=COLORIZE_MIDPOINT)
                    data_img = data_img.convert('RGBA')
                    data_img.putalpha(mask)

                # Resize to fit text height
                if data_img.height > font_ascent:
                    # Can be silent about this
                    img_ratio = data_img.width / data_img.height
                    target_width = int( img_ratio * font_ascent )
                    data_img = data_img.resize( (target_width, font_ascent),
                            resample=PIL.Image.Resampling.LANCZOS )
                # Center it vertically
                img_y = position[1] + ( (font_ascent + font_descent) // 2 ) - ( data_img.height // 2 )
                # Draw
                img.alpha_composite( data_img,
                    dest=( position[0] + width, img_y ) )

            width += data_img.width
        else:
            text = None
            color = None
            if kw_type == KeywordData.REGULAR:
                text = kw[1]
                color = default_color
            else:
                text, color = kw[1:]
                if color is None:
                    color = COLOR_KEYWORD
            if not query_width:
                draw.text( ( position[0] + width, position[1]),
                        text,
                        font=font,
                        fill=color )
            width += int( ceil(draw.textlength( text, font )) )
    return width

def wrap_keywords( draw, font, keywords, width ):
    '''
    Wraps an array of keywords (returned by `get_keywords`) into a 2D array.
    Each entry of the 2D array represents a single line which fits in the specified width.

    @param draw a PIL.ImageDraw instance
    @param font the font to draw in
    @param keywords an array of keyworsd, returne by `get_keywords`
    @param width the width to perform word wrap on.

    @return a 2D array of keywords
    '''
    wrapped = []
    current = []

    for kw in keywords:
        if kw[0] == KeywordData.BREAK:
            if len(current) != 0:
                wrapped.append(current)
                current = []
            continue

        if len(current) == 0:
            delta = [ kw ]
        else:
            delta = current + [ kw ]

        # Use `draw_keywords` to query the width of the next (delta) addition
        if draw_keywords( delta, draw, font ) > width:
            # Always draw at least 1 keyword element, otherwise we are stuck
            if len(current) == 0:
                wrapped.append(delta)
            else:
                wrapped.append(current)
                current = [ kw ]
        else:
            current = delta

    # Don't forget the last line!
    if len(current) != 0:
        wrapped.append(current)

    return wrapped

def add_text( asset_path, keyword_data, img, data ):
    draw = PIL.ImageDraw.Draw( img )
    font = PIL.ImageFont.truetype( DESC_TEXT_FONT, DESC_TEXT_SIZE )
    font_ascent, font_descent = font.getmetrics()

    # First, add the preamble, if it exists
    preamble = get_field( data, 'preamble' )
    current_offset_y = TEXT_UP
    if preamble:
        preamble = get_keywords( preamble, keyword_data )
        preamble = wrap_keywords( draw, font, preamble, TEXT_RIGHT - TEXT_LEFT )
        for keywords in preamble:
            draw_keywords( keywords,
                    draw,
                    font,
                    img=img,
                    position=( TEXT_LEFT, current_offset_y ),
                    default_color=COLOR_DESC,
                    query_width=False )
            current_offset_y += font_ascent
        current_offset_y += DICE_SPACER

    # Then add all the dice
    for dice in get_field( data, 'dice' ):
        dice_type = dice['type'].lower()
        if dice_type in ['block', 'block_counter', 'evade', 'evade_counter']:
            dice_color = COLOR_DEFENSE
        else:
            dice_color = COLOR_OFFENSE

        dice_img_path = os.path.join( asset_path, 'ruina', dice_type + '.png' )
        dice_img = PIL.Image.open( dice_img_path )

        height = 0
        dice_range = get_keywords( dice['range'], keyword_data )
        dice_effect = dice.get('effect', None)
        if dice_effect:
            dice_effect = get_keywords( dice_effect, keyword_data )
            effect_offset_x = dice_img.width + draw_keywords( dice_range, draw, font ) + TEXT_SPACER + TEXT_LEFT
            dice_effect = wrap_keywords( draw,
                    font,
                    dice_effect,
                    TEXT_RIGHT - effect_offset_x )
            for keywords in dice_effect:
                draw_keywords( keywords,
                        draw,
                        font,
                        img=img,
                        position=( effect_offset_x, current_offset_y + height ),
                        default_color=dice_color,
                        query_width=False )
                height += font_ascent
        else:
            if font_ascent > dice_img.height:
                height = font_ascent
            else:
                height = dice_img.height

        # Draw range
        draw_keywords( dice_range,
            draw,
            font,
            img=img,
            position=(dice_img.width + TEXT_LEFT,
            current_offset_y + (height // 2) - ( (font_ascent + font_descent) // 2)),
            default_color=dice_color,
            query_width=False )

        # Draw dice icon
        img.alpha_composite( dice_img,
                dest=(TEXT_LEFT, current_offset_y + (height // 2) - (dice_img.height // 2)) )

        current_offset_y += height + DICE_SPACER

    return img

def main(data_path, output_path, asset_path, keyword_path, is_mini=False):
    psd_path = os.path.join(asset_path, PSD_NAME)
    with open(psd_path, 'rb') as check_psd:
        check_md5 = hashlib.file_digest(check_psd, 'md5').hexdigest()
        assert check_md5 == PSD_MD5, \
                'MD5 sum for %s did not match expected (%s!=%s), wrong psd supplied!' % (psd_path,
                check_md5,
                PSD_MD5)
    psd = PSDImage.open(psd_path)
    data = init_data('', data_path)
    keyword_data = init_data('', keyword_path)

    # Toggle layers
    edit_page_class(psd, data)

    # Force redraws the psd instead of grabbing from the cache / buf
    img = psd.composite(force=True)

    # Add custom title and text
    img = add_title( img, data )
    img = add_cost( asset_path, img, data )

    if is_mini:
        # Crop the image to minify it
        img = img.crop( (MINI_LEFT, MINI_UP, MINI_RIGHT, MINI_DOWN) )
    else:
        # Only need to add text if not mini (it would be entirely cropped otherwise)
        img = add_text( asset_path, keyword_data, img, data)

    img.save(output_path, format='PNG') # Finally, output to png

def get_args():
    # Parse command line using the built-in argparse library
    parser = argparse.ArgumentParser()
    parser.add_argument('data_path', type=str, help='Path to data to create a card')
    parser.add_argument('output_path', type=str, help='Path to output (ought to be a png file)')
    parser.add_argument('-m', '--mini', action='store_true', default=False,
            help='A mini card (just the cover)')
    parser.add_argument('-a', '--asset-path', type=str, default=None,
            help='Path to the assets folder. Defaults to ../assets (relative to this script)')
    parser.add_argument('-k', '--keyword-path', type=str, default=None,
            help='Path to keywords JSON. Defaults to ../assets/keywords.json (also relative)')
    args = parser.parse_args()

    # As stated in the help text, `<scriptdir>/../assets/`
    if args.asset_path is None:
        args.asset_path = os.path.join(
            os.path.dirname(sys.argv[0]),
            '..',
            'assets')
    if args.keyword_path is None:
        args.keyword_path = os.path.join(
            os.path.dirname(sys.argv[0]),
            '..',
            'assets',
            'keywords.json')
    return (args.data_path, args.output_path, args.asset_path, args.keyword_path, args.mini)

if __name__ == '__main__':
    main(*get_args())

