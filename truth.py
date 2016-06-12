import sqlite3

_t = sqlite3.connect("truth.mdb")

valkyria = [185, 235, 188, 214, 189]
natsuki5 = [238, 238, 238, 238, 238]

def ssrteam_for_charas(charas):
    ret = []

    for chara_id in charas:
        uid, rarity = _t.execute("SELECT id, rarity FROM card_data WHERE chara_id = ? OR id = ? ORDER BY rarity DESC LIMIT 1", (chara_id, chara_id)).fetchone()
        if rarity < 7:
            print("Warning: no SSR for charaid", chara_id, " so a card with rarity", rarity, "will be substituted")
        ret.append(uid)
    return ret

def to_ssr_team(in_team):
    ret = []

    for unit_id in in_team:
        chara_id = _t.execute("SELECT chara_id FROM card_data WHERE id = ?", (unit_id,)).fetchone()

        if chara_id is None:
            ret.append(unit_id)
            continue
        else:
            chara_id = chara_id[0]

        uid, rarity = _t.execute("SELECT id, rarity FROM card_data WHERE chara_id = ? ORDER BY rarity DESC LIMIT 1", (chara_id,)).fetchone()

        if rarity < 7:
            print("Warning: no SSR for charaid", chara_id, " so a card with rarity", rarity, "will be substituted")

        ret.append(uid)
    return ret

def get_chars():
    ret = []
    for k, in _t.execute("SELECT chara_id FROM chara_data"):
        uid = _t.execute("SELECT id, rarity FROM card_data WHERE chara_id = ? ORDER BY rarity DESC LIMIT 1", (k,)).fetchone()
        ret.append((k, uid))
    return ret

def get_cards():
    return [k for k, in _t.execute("SELECT id FROM card_data where series_id = id order by rarity")]
