import sqlite3

_t = sqlite3.connect("truth.mdb")

valkyria = [185, 235, 188, 214, 189]

def ssrteam_for_charas(charas):
    ret = []

    for chara_id in charas:
        uid, rarity = _t.execute("SELECT id, rarity FROM card_data WHERE chara_id = ? ORDER BY rarity DESC LIMIT 1", (chara_id,)).fetchone()
        if rarity < 7:
            print("Warning: no SSR for charaid", chara_id, " so a card with rarity", rarity, "will be substituted")
        ret.append(uid)
    return ret

def to_ssr_team(in_team):
    ret = []

    for unit_id in in_team:
        chara_id = _t.execute("SELECT chara_id FROM card_data WHERE id = ?", (unit_id,)).fetchone()[0]
        uid, rarity = _t.execute("SELECT id, rarity FROM card_data WHERE chara_id = ? ORDER BY rarity DESC LIMIT 1", (chara_id,)).fetchone()
        if rarity < 7:
            print("Warning: no SSR for charaid", chara_id, " so a card with rarity", rarity, "will be substituted")
        ret.append(uid)
    return ret
