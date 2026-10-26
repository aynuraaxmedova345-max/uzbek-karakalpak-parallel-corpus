"""Leksikon moslashtiruvchisi uchun tezkor testlar: python scripts/comments/test_lexicon.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon import LexiconMatcher, normalize  # noqa: E402

M = LexiconMatcher()


def items(text, lexicon=None):
    return [m.item for m in M.find(text) if lexicon in (None, m.lexicon)]


def has(text, needle, lexicon="frazeologik"):
    found = items(text, lexicon)
    assert any(needle in i for i in found), f"{needle!r} topilmadi: {text!r} -> {found}"


def hasnt(text, needle, lexicon=None):
    found = items(text, lexicon)
    assert not any(needle in i for i in found), f"{needle!r} xato topildi: {text!r} -> {found}"


# Normallashtirish: kirill, tutuq belgilari
assert normalize("Кўнглим ғаш") == "ko'nglim g'ash"
assert normalize("A’ZOYI o‘g‘il") == "azoyi o'g'il"

# Iboralar: qo'shimchalar, kirill, tutuq belgisisiz yozuv, variantlar
has("a'zoyi badanimdan sovuq ter chiqib ketdi", "a’zoyi badan(i)dan sovuq ter chiqib ketdi")
has("Юрагим дов бермади", "yurag(i) dov bermadi")
has("adabini berib qo'yish kerak", "adab(i)ni bermoq")
has("kalavaning uchini topolmay qoldik", "kalavaning uchini topmoq")
has("Bu odamning boshi osmonda", "bosh(i) osmonda")
has("oq-qorani ajratolmaydigan odamlar", "oq-qorani ajratmoq")
has("Kozim uchib turibdi", "ko‘z(i) uchib")          # tutuq belgisisiz
has("ishni qoldan chiqarib yubordi", "qo‘ldan chiq")   # tutuq belgisisiz

# Noto'g'ri mosliklar bo'lmasligi kerak
hasnt("Zo'r video, rahmat!", "")
hasnt("boshlanib, ustyurt platosi", "bosh ustiga")    # bosh != boshlanib
hasnt("qoldik, hammasi chigal", "qo‘ldan")            # qol != qo'l
hasnt("birga, dunyoda", "bir dunyo")                  # tinish belgisi orqali emas
hasnt("bularni ko'rdim", "bulamoq", "kochma")         # vazifadosh so'z
hasnt("uch kishi keldi", "uchmoq", "kochma")          # uch (son) != uchmoq

# Ko'chma so'zlar
assert "chigal" in items("hammasi chigal bo'lib ketdi", "kochma")

print("Barcha testlar o'tdi.")
