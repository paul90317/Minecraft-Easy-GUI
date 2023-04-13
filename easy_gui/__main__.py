import yaml
from yaml.loader import SafeLoader
import sys
import os
import json
from zipfile import ZipFile
from os import path


def template(code: str, pattern: dict[str, int | str]) -> str:
    for k, v in pattern.items():
        code = code.replace(f'<{k}>', str(v))
    return code


def write_code(code: str, filename: str) -> None:
    dirname = path.dirname(filename)
    if len(dirname) > 0:
        os.makedirs(dirname, exist_ok=True)
    with open(filename, 'w')as f:
        f.write(code)


def get_resource(filename: str) -> str:
    parent = path.dirname(__file__)
    if len(parent) == 0:
        return open(filename, 'r').read()
    elif path.isfile(parent):
        return ZipFile(parent).open(filename, 'r').read().decode(encoding='utf-8')
    else:
        return open(path.join(parent, filename), 'r').read()


def update_values(new_values: set, filename: str) -> None:
    if os.path.isfile(filename):
        with open(filename, 'r')as f:
            for item in json.load(f)['values']:
                new_values.add(item)
    write_code(json.dumps({
        "values": list(new_values)
    }), filename)


class Item:
    def __init__(self, data: dict) -> None:
        self.id = data['id']
        self.enchant = data.get('enchant', False)
        self.text = data.get('text', '')
        self.color = data.get('color', None)
        self.tag = data.get('tag', {})


class Slot:
    LABEL_ENTRY = get_resource('template/slot_type/label/entry.mcfunction')
    LABEL_EH = get_resource('template/slot_type/label/eh.mcfunction')
    N_LEFT_ENTRY = get_resource('template/slot_type/n_left/entry.mcfunction')
    N_LEFT_EH = get_resource('template/slot_type/n_left/eh.mcfunction')
    DROP_ENTRY_IF = get_resource('template/slot_type/drop/entry_if.mcfunction')
    DROP_ENTRY_UNLESS = get_resource(
        'template/slot_type/drop/entry_unless.mcfunction')
    DROP_EH = get_resource('template/slot_type/drop/eh.mcfunction')
    LABEL_ITEMS = {'cookie'}

    @staticmethod
    def codeGen(tile_id: str, slot: str | int, object: dict) -> tuple[str, str]:
        slot_type = object['type']
        if slot_type == 'label':
            item = Item(object['item'])
            click = object.get('click', '')
            Slot.LABEL_ITEMS.add(item.id)
            return (
                template(Slot.LABEL_ENTRY, {
                    'slot': slot,
                    'id': tile_id
                }),
                template(Slot.LABEL_EH, {
                    'slot': slot,
                    'item': item.id,
                    'text': item.text,
                    'color': f',"color":"{item.color}"' if item.color is not None else '',
                    'enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if item.enchant else '',
                    'click': click
                })
            )
        elif slot_type == 'n_left':
            n: int = object['n']
            return (
                template(Slot.N_LEFT_ENTRY, {
                    'slot': slot,
                    'id': tile_id,
                    'n_add_one': n+1
                }),
                template(Slot.N_LEFT_EH, {
                    'slot': slot,
                    'n': n
                })
            )
        elif slot_type == 'drop':
            cond: str = object.get('cond', 'undefined')
            tag: str = object.get('tag', None)
            data: str = object.get('data', None)
            item_id: str = object.get('id', None)
            if cond == 'if':
                return (
                    template(Slot.DROP_ENTRY_IF, {
                        'slot': slot,
                        'tile_id': tile_id,
                        'tag': f',tag:{tag}' if tag is not None else '',
                        'item_id': f',id:"{item_id}"'if item_id is not None else '',
                        'data': f'.tag.{data}' if data is not None else ''
                    }),
                    template(Slot.DROP_EH, {
                        'slot': slot
                    })
                )
            elif cond == 'unless':
                return (
                    template(Slot.DROP_ENTRY_UNLESS, {
                        'slot': slot,
                        'tile_id': tile_id,
                        'tag': f',tag:{tag}' if tag is not None else '',
                        'item_id': f',id:"{item_id}"'if item_id is not None else '',
                        'data': f'.tag.{data}' if data is not None else ''
                    }),
                    template(Slot.DROP_EH, {
                        'slot': slot
                    })
                )
            elif cond == 'never':
                return (
                    '',
                    template(Slot.DROP_EH, {
                        'slot': slot
                    })
                )
            elif cond == 'always':
                return (
                    template(Slot.DROP_ENTRY_IF, {
                        'slot': slot,
                        'tile_id': tile_id,
                        'tag': '',
                        'item_id': '',
                        'data': ''
                    }),
                    template(Slot.DROP_EH, {
                        'slot': slot
                    })
                )
            else:
                exit(f'error: unknown condiction {cond} of drop slot type')
        else:
            exit(f'error: unknown slot type {slot_type}')


with open(sys.argv[1], 'r') as f:
    data: dict = yaml.load(f, Loader=SafeLoader)

tile_id = data['id']
container_block = Item(data['entity']['block'])
container_item = Item(data['entity']['item'])
setblock = data.get('setblock', 'destroy')
entries = template(get_resource('template/tile/tick.mcfunction'), {
    "id": tile_id,
    "block": container_block.id
})
for slots, object in data['slot'].items():
    slots = str(slots).split(',')
    for slot in slots:
        if slot.find('..') != -1:
            f, t = slot.split("..")
            f = int(f)
            t = int(t)
            for i in range(f, t + 1):
                entry, eh = Slot.codeGen(tile_id, i, object)
                write_code(
                    eh, f'data/eg/functions/tile/{tile_id}/slot/{i}/eh.mcfunction')
                entries += entry
        else:
            entry, eh = Slot.codeGen(tile_id, slot, object)
            write_code(
                eh, f'data/eg/functions/tile/{tile_id}/slot/{slot}/eh.mcfunction')
            entries += entry
entries += data.get('tick', '')
write_code(entries,
           f'data/eg/functions/tile/{tile_id}/tick.mcfunction')

write_code(template(get_resource('template/tile/search/item_frame.mcfunction'), {
    "id": tile_id
}),
    f'data/eg/functions/tile/{tile_id}/search/item_frame.mcfunction')

spawn_egg = data.get('spawn_egg', None)
if spawn_egg is not None:
    spawn_egg = Item(spawn_egg)
    write_code(template(get_resource('template/tile/spawn_egg.mcfunction'), {
        "id": tile_id,
        'spawn_egg': spawn_egg.id,
        'text': spawn_egg.text,
        'color': f',"color":"{spawn_egg.color}"' if spawn_egg.color is not None else '',
        'enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if spawn_egg.enchant else ''
    }),
        f'data/eg/functions/tile/{tile_id}/spawn_egg.mcfunction')

    write_code(template(get_resource('template/tile/spawn_egg.json'), {
        "id": tile_id,
        'spawn_egg': spawn_egg.id,
        'text': spawn_egg.text,
        'color': f',\\"color\\":\\"{spawn_egg.color}\\"' if spawn_egg.color is not None else '',
        'enchant': ',Enchantments:[{id:\\"minecraft:binding_curse\\",lvl:1}]' if spawn_egg.enchant else ''
    }),
        f'data/eg/loot_tables/{tile_id}.json')

    write_code(template(get_resource('template/tile/search/area_effect_cloud.mcfunction'), {
        "id": tile_id
    }),
        f'data/eg/functions/tile/{tile_id}/search/area_effect_cloud.mcfunction')

    write_code(template(get_resource(f'template/tile/destroy_{setblock}.mcfunction'), {
        "id": tile_id,
        "block": container_block.id
    }),
        f'data/eg/functions/tile/{tile_id}/destroy.mcfunction')

    write_code(template(get_resource('template/tile/try_spawn/cancel.mcfunction'), {
        "id": tile_id
    }),
        f'data/eg/functions/tile/{tile_id}/try_spawn/cancel.mcfunction')

    write_code(template(get_resource('template/tile/try_spawn/check.mcfunction'), {
        "id": tile_id
    }),
        f'data/eg/functions/tile/{tile_id}/try_spawn/check.mcfunction')

    update_values({f"eg:tile/{tile_id}/search/area_effect_cloud"},
                  'data/eg/tags/functions/search/area_effect_cloud.json')

    write_code(template(get_resource('template/tile/try_spawn/load.mcfunction'), {
        "id": tile_id,
        'item': container_item.id,
        'item_text': container_item.text,
        'item_color': f',"color":"{container_item.color}"' if container_item.color is not None else '',
        'item_enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if container_item.enchant else '',
        'block': container_block.id,
        'block_text': container_block.text,
        'block_color': f',"color":"{container_block.color}"' if container_block.color is not None else '',
    }),
        f'data/eg/functions/tile/{tile_id}/try_spawn/load.mcfunction')
else:
    dropped_item = Item(data['dropped_item'])
    tag = ''
    for k, v in dropped_item.tag.items():
        tag += f',{k}:{v}'
    write_code(template(get_resource('template/tile_dropped_item/dropped_item.mcfunction'), {
        "id": tile_id,
        'item': dropped_item.id,
        'text': dropped_item.text,
        'color': f',"color":"{dropped_item.color}"' if dropped_item.color is not None else '',
        'enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if dropped_item.enchant else '',
        'tag': tag
    }),
        f'data/eg/functions/tile/{tile_id}/dropped_item.mcfunction')

    write_code(template(get_resource('template/tile_dropped_item/dropped_item.json'), {
        "id": tile_id,
        'item': dropped_item.id,
        'text': dropped_item.text,
        'color': f',\\"color\\":\\"{dropped_item.color}\\"' if dropped_item.color is not None else '',
        'enchant': ',Enchantments:[{id:\\"minecraft:binding_curse\\",lvl:1}]' if dropped_item.enchant else '',
        'tag': tag
    }),
        f'data/eg/loot_tables/{tile_id}.json')

    write_code(template(get_resource('template/tile/search/item.mcfunction'), {
        "id": tile_id
    }),
        f'data/eg/functions/tile/{tile_id}/search/item.mcfunction')

    destroy = data.get('destroy', None)
    write_code(template(get_resource(f'template/tile_dropped_item/destroy_{setblock}.mcfunction'), {
        "id": tile_id,
        "block": container_block.id,
        'load': f'execute positioned ~ ~-1 ~ run {destroy}' if destroy is not None else '',
        'item': dropped_item.id,
        'text': dropped_item.text,
        'color': f',"color":"{dropped_item.color}"' if dropped_item.color is not None else '',
        'enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if dropped_item.enchant else '',
        'tag': tag
    }),
        f'data/eg/functions/tile/{tile_id}/destroy.mcfunction')

    write_code(template(get_resource('template/tile_dropped_item/try_spawn/check.mcfunction'), {
        "id": tile_id
    }),
        f'data/eg/functions/tile/{tile_id}/try_spawn/check.mcfunction')

    update_values({f"eg:tile/{tile_id}/search/item"},
                  'data/eg/tags/functions/search/item.json')

    load = data.get('load', None)
    write_code(template(get_resource('template/tile_dropped_item/try_spawn/load.mcfunction'), {
        'load': f'execute positioned ~ ~1 ~ run {load}' if load is not None else '',
        "id": tile_id,
        'item': container_item.id,
        'item_text': container_item.text,
        'item_color': f',"color":"{container_item.color}"' if container_item.color is not None else '',
        'item_enchant': ',Enchantments:[{id:"minecraft:binding_curse",lvl:1}]' if container_item.enchant else '',
        'block': container_block.id,
        'block_text': container_block.text,
        'block_color': f',"color":"{container_block.color}"' if container_block.color is not None else '',
    }),
        f'data/eg/functions/tile/{tile_id}/try_spawn/load.mcfunction')

update_values(Slot.LABEL_ITEMS,
              'data/eg/tags/items/label.json')

update_values({f"eg:tile/{tile_id}/search/item_frame"},
              'data/eg/tags/functions/search/item_frame.json')

write_code(get_resource('template/game/tick.mcfunction'),
           'data/eg/functions/tick.mcfunction')

write_code(get_resource('template/game/load.mcfunction'),
           'data/eg/functions/load.mcfunction')

if not os.path.exists('pack.mcmeta'):
    write_code(json.dumps({
        "pack": {
            "pack_format": 10,
            "description": ""
        }
    }),
        'pack.mcmeta')

update_values({"eg:tick"},
              'data/minecraft/tags/functions/tick.json')

update_values({"eg:load"},
              'data/minecraft/tags/functions/load.json')
