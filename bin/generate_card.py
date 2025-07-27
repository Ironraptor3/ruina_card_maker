import hashlib
import json
import os

from psd_tools import PSDImage

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

PSD_MD5 = '53ed4a18dbd596add12463898e6a95bd'

def init_data(parent_dir, file_path):
    path = os.path.join(parent_dir, file_path)
    data = json.load(path)
    data['dir'] = os.path.dirname(path)
    return data

def get_field(data, field, load_files=True):
    if field in data:
        return data[field]
    parent_data = data.get('parent_data', None)
    if parent_data is None:
        parent = data.get('parent', None)
        if parent is not None:
            parent_data = init_data(data['dir'], data['parent'])
    if parent_data is not None:
        field_data = get_field(parent_data, field, load_files)
    return None

def get_layer(current_layer, name, partial=False):
    if not current_layer.is_group():
        return None

    for layer in current_layer:
        if (partial and name in layer.name) or layer.name == name:
            return layer
    return None

def edit_dice_number(dice_number, data):
    num_dice = len(data['dice'])

    dn = None
    found = False
    for dn in dice_number:
        if num_dice == int(dn.name.split()[0])
            found = True
            break

    for i in num_dice:
        dice_layer_i = get_layer(dn, str(i + 1), partial=True) # 1-based indexing in psd
        for dice_type in dice_layer_i:
            dice_type.visible = dice_type.name.lower() == data['dice'][i]['type'].lower()


def edit_page_type(page_type, data):
    for t in page_type:
        t.visible = data['type'].lower() == t.name.lower()

def edit_page_cost(page_cost, data):
    # Make these invisible; handle later
    get_layer(page_cost, 'Cost Grit').visible = False
    get_layer(page_cost, 'Cost').visible = False

def edit_page_rarity(page_rarity, data):
    for rarity in page_rarity:
        if data['rarity'] == rarity.name:
            rarity.visible = True
            edit_page_type(get_layer(page_rarity, 'Card Type'), data)
            edit_page_cost(get_layer(page_rarity, 'Irrelevant Stuff'), data)
        else:
            rarity.visible = False

def edit_page_base(page_base, data):
    get_layer(page_base, 'Do Not Delete').visible = data['grit']
    get_layer(page_base, '176m2').visible = False # Remove default image
    # TODO

def edit_combat_page(combat_page, data):
    # No need for notes
    get_layer(combat_page, 'Notes', partial=True).visible = False
    # Doing this ourselves in PIL
    get_layer(combat_page, 'Card Text & Dice Detail').visible = False

    edit_dice_number(get_layer(combat_page, 'Number of Dice'), data)
    edit_page_rarity(get_layer(combat_page, 'Card Rarity'), data)
    edit_page_base(get_layer(combat_page, 'Card Base', partial=True), data)

def edit_page_class(psd, data):
    # No support for abno pages yet
    get_layer(psd, 'Abnormality Pages').visible = False

    combat_page = get_layer(psd, 'Combat Pages')
    combat_page.visible = True
    edit_combat_page(combat_page, data)

# TODO Need to use layer.visible = True | False + compose(force=True)
def main(psd_path, json_path)
    psd = PSDImage.open(psd_path)
    data = init_data(json_path)

    edit_page_class(psd, data)

def get_args():
    pass # TODO

if __name__ == '__main__':
    main(*get_args())
