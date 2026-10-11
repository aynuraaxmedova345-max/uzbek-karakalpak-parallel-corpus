"""Termin tasnifi uchun lug'atlar (lemma shaklida, normallashtirilgan apostrof: ʻ, ʼ).

Barcha ro'yxatlar shu loyiha uchun tuzilgan va qo'lda tekshirilishi mumkin; har bir avtomatik qaror
qaysi ro'yxat/qoidaga tayanganini classify_terms.py `auto_sabab` ustunida ko'rsatadi.
"""

# --- 1. Tor huquqiy leksika (bir so'zli termin yoki birikmaning huquqiy komponenti) -------------
LEGAL = set("""
konvensiya shartnoma pakt protokol bayonnoma ratifikatsiya ratifikatsion denonsatsiya depozitariy deklaratsiya
ustav nizom statut bitim kelishuv ahdlashuv implementatsiya majburiyat huquq huquqiy qonunchilik qonun kodeks
norma prinsip tamoyil yurisdiksiya suverenitet vakolat vakolatli vakolatxona konsul konsullik diplomatik diplomatiya
delegat delegatsiya immunitet imtiyoz daxlsizlik fuqarolik fuqaro fuqaroviy fuqarolik-huquqiy ishtirokchi-davlat
ahdlashuvchi ishtirokchi tomon sud sudlov sudlanganlik sudlanuvchi hukm jazo jinoyat jinoiy jinoyatchi qilmish
huquqbuzarlik qoidabuzarlik ayblanuvchi jabrlanuvchi guvoh guvohlik tergov taʼqib ekstraditsiya musodara ekspertiza
protsessual protsedura protsess instansiya arbitraj iltimosnoma soʻrovnoma talabnoma topshiriq aliment meros
merosxoʻr vasiyatnoma vasiyat vasiylik vasiy farzandlik nikoh mulk mulkiy mol-mulk notarial legallashtirish korrupsiya
terrorizm terroristik ekstremizm separatizm transmilliy kamsitish kamsitilish diskriminatsiya qiynoq irqiy tenglik
erkinlik layoqat layoqatsiz layoqatlilik javobgarlik javobgar kompensatsiya tovon zarar asir asirlik yarador kombatant
gospital lazaret sanitar sanitariya emblema istilo istilochi betaraf homiy homiylik rekvizitsiya repressaliy mojaro
insonparvarlik dalolatnoma fakultativ yorliq xabarnoma bildirishnoma guvohnoma ishonchnoma dalil petitsiya petitsiyachi
maʼmuriy intizomiy mansabdor prokuratura adliya mahkama subyekt reglament kvorum kotibiyat qoʻmita komissiya
assambleya nizo ozodlik qamoq tranzit internirlash deportatsiya qochqin fuqaroligi taomil tartib-taomil
rozilik xatti-harakat qadr-qimmat
""".split())

# Umumiy bosh so'z bilan birga kelganda birikmani xalqaro-huquqiy qiladigan soha aniqlovchilari
DOMAIN_MOD = set("""
qurolli harbiy xalqaro davlat tibbiy tibbiyot sanitariya sanitariya-transport diniy manfaatdor xavfsizlik odam
farqlovchi fuqarolik maʼmuriy betaraf dushman tinch fuqaro diplomatik konsullik insonparvarlik
""".split())

# Lemma ketma-ketligi bo'yicha qat'iy fe'liy terminlar (huquqiy komponentsiz bo'lsa ham)
FIXED_VERBAL = {"kuch kir", "vatan qaytar", "kuch kirish"}

# Birikmada bosh so'z bo'lganda huquqiy tushunchani nomlashi mumkin bo'lgan umumiyroq otlar
HEAD_GENERAL = set("""
davlat organ shaxs aholi kuch harakat yordam muassasa hudud ish xodim vakil kotib hujjat matn qaror chora tadbir
maqom munosabat tizim tartib mexanizm hisobot maʼruza axborot organlar kafolat himoya muhofaza zona lager kema
apparat belgi kartochka guvohnoma xizmat bitim jamgʻarma fond mablagʻ daromad faoliyat tashkilot kengash markaz
muhokama mamlakat loyiha muddat jarayon holat qurbon boshliq konferensiya aʼzo asos hamkorlik standart obyekt
vosita tuzilma xavfsizlik savdo institut
""".split())

# Birikma ichida bo'lsa, uni erkin sintaktik birikma qiladigan so'zlar (olmosh, belgilovchi, miqdor)
DETERMINERS = set("""
oʻz oʻzi oʻzining oʻzlarining ushbu mazkur shu bu har barcha hamma biror birorta biron biron-bir biror-bir hech
qanday qaysi boshqa ayrim baʼzi koʻp eng ikkala har bir oʻsha shunday bunday
""".split())
CONJ = {"va", "yoki", "hamda", "yoxud", "ham"}
LIGHT_VERB_NOUNS = set("""
amal oshir old ol koʻr koʻrsat et qil ber tur
""".split())
MONTHS = set("yanvar fevral mart aprel may iyun iyul avgust sentabr sentyabr oktabr oktyabr noyabr dekabr yil".split())

# --- 2. Nomenklatura: joy va atoqli nomlar, tashkilot bosh so'zlari ------------------------------
PROPER = set("""
oʻzbekiston qoraqalpogʻiston qirgʻiziston qozogʻiston turkmaniston tojikiston afgʻoniston armaniston ozarbayjon
rossiya belarus ukraina moldova gruziya xitoy shveysariya yevropa jeneva nyu-york vena toshkent kishinyov kishinev
palermo shanxay gaaga amerika osiyo birlashgan millat qizil xoch yarim oy minsk almati bishkek dushanbe kobul
""".split())
ORG_HEADS = set("""
tashkilot vazirlik qoʻmita kengash assambleya mahkama majlis palata prokuratura agentlik byuro markaz kotibiyat
komissiya bank fond xizmat federatsiya konfederatsiya ittifoq hamdoʻstlik respublika qoʻmitasi prezident
""".split())
# Ko'p so'zli birikmada doim nom bo'ladigan tashkilot bosh so'zlari (bosh harf talab qilinmaydi)
ORG_HEADS_ALWAYS = set("vazirlik assambleya mahkama palata prokuratura agentlik kotibiyat".split())
NAME_PAIRS = [{"birlashgan", "millat"}, {"qizil", "xoch"}, {"yarim", "oy"}, {"qizil", "yarim"}]
ORG_ABBR = set("bmt shht mdh iiv dxx tiv yuneskо yunisef".split())

# --- 3. Mavzuiy guruhlar (tartib = ustuvorlik) ---------------------------------------------------
GROUPS = [
    ("diplomatik_konsullik", set("""diplomatik diplomatiya diplomat konsul konsullik elchi elchixona vakolatxona missiya
        delegat delegatsiya immunitet imtiyoz daxlsizlik akkreditatsiya nota martaba unvon""".split())),
    ("shartnoma_jarayoni", set("""ratifikatsiya ratifikatsion denonsatsiya depozitariy imzola imzolash imzo qoʻshilish
        yorliq rezervatsiya izoh muzokara implementatsiya tuzatish talqin kuchga""".split())),
    ("gumanitar_huquq", set("""asir asirlik yarador bemor kombatant gospital lazaret sanitar sanitariya emblema xoch istilo
        istilochi homiy homiylik betaraf qurolli harbiy mojaro urush insonparvarlik internirlash rekvizitsiya repressaliy
        halokat lager fuqaro-aholi tinch kema-lazaret tibbiy tibbiyot sanitariya-transport dushman kombatant
        qurbon""".split())),
    ("inson_huquqlari", set("""inson kamsitish kamsitilish diskriminatsiya qiynoq irqiy irq tenglik erkinlik bola
        xotin-qiz ayol nogironlik qadr-qimmat shafqatsiz gʻayriinsoniy fuqaroviy siyosiy ijtimoiy madaniy iqtisodiy
        oʻlim fohishabozlik pornografiya rozilik qadr-qimmat""".split())),
    ("nizolar_va_javobgarlik", set("""nizo javobgarlik javobgar zarar ziyon tovon kompensatsiya arbitraj sanksiya
        nizolashayotgan""".split())),
    ("huquqiy_yordam_va_jinoiy_protsess", set("""sud sudlov sudlanganlik sudlanuvchi hukm jazo jinoyat jinoiy jinoyatchi
        qilmish ayblanuvchi jabrlanuvchi guvoh guvohlik tergov taʼqib ekstraditsiya berish musodara iltimosnoma soʻrovnoma
        talabnoma topshiriq adliya notarial aliment meros merosxoʻr vasiyat vasiyatnoma vasiylik vasiy nikoh farzandlik
        ekspertiza protsessual korrupsiya terrorizm terroristik ekstremizm separatizm legallashtirish transmilliy mansabdor
        huquqbuzarlik qoidabuzarlik prokuratura qamoq ozodlik yordam savdo jinoyatchi""".split())),
    ("xalqaro_tashkilotlar", set("""tashkilot qoʻmita komissiya assambleya kengash kotibiyat kotib byuro agentlik
        tashkiliy""".split())),
    ("huquq_manbalari_va_hujjatlar", set("""konvensiya shartnoma pakt protokol bayonnoma deklaratsiya ustav nizom statut
        bitim kelishuv kodeks qonun qonunchilik norma prinsip tamoyil hujjat matn ilova qoida""".split())),
    ("subyektlar", set("""davlat ishtirokchi-davlat ishtirokchi ahdlashuvchi tomon fuqaro shaxs organ xalq millat
        subyekt vakil fuqarolik""".split())),
]

# --- 4. Sinonim (dublet) juftlari: komponent darajasida ------------------------------------------
SYNONYMS = [
    {"protokol", "bayonnoma"}, {"ratifikatsiya", "tasdiqlash"}, {"diskriminatsiya", "kamsitish"},
    {"fuqaroviy", "fuqarolik"}, {"prinsip", "tamoyil"}, {"nizom", "ustav"}, {"tovon", "kompensatsiya"},
    {"ahdlashuvchi", "ishtirokchi"}, {"tomon", "davlat"}, {"bitim", "kelishuv"}, {"iltimosnoma", "soʻrovnoma"},
    {"insonparvarlik", "gumanitar"}, {"protsedura", "taomil", "tartib-taomil"}, {"gospital", "kasalxona", "shifoxona"},
    {"ishtirokchi-davlat", "ishtirokchi davlat"}, {"xalqaro", "baynalmilal"}, {"norma", "qoida"},
    {"zarar", "ziyon"},
]

# --- 5. Kelib chiqish (o'zak bo'yicha). Faqat ishonchli ma'lum bo'lgan o'zaklar ------------------
UZ = "oʻzbekcha"
AP = "arabcha-forscha"
RU = "ruscha-baynalmilal"
ETYM = {}
for w in """erk erkin bitim kelishuv kengash yordam tergov qamoq soʻrov ish yer suv bola ota ona qiz kuch qurol urush
tinch oʻlim yigʻim toʻlov bosh ichki tashqi yuqori tovon berish ber topshir topshiriq yuk dengiz qoʻshin yorliq
oʻz koʻch koʻchir tan ol qil et tur tut qoʻy qoʻl oy kun yil qoʻshma oldi tuz yoz yozma bilim oq qora yarim
qidir qidiruv tekshir tekshiruv soʻr tutqun tuzil teng boshqaruv yigʻilish""".split():
    ETYM[w] = UZ
for w in """huquq qonun davlat hukm jinoyat adliya muassasa vakil vakolat taʼqib ahd shart shartnoma majburiyat masʼul
javob javobgar xalq xalqaro inson hurmat ozod mahkama qaror qoida tartib tamoyil nizom ilova iltimos maʼmur intizom
mansab mansabdor fuqaro aholi hudud mulk meros vasiy vasiyat nikoh farzand shaxs millat muhofaza himoya harb asir
istilo homiy betaraf yarador bemor mojaro zarar ziyon daʼvo isbot dalil guvoh jazo ayb musodara taʼmin idora maʼlumot
axborot kotib majlis tashkilot vazir imtiyoz daxl bayon xabar imzo muhr nusxa matn modda band qism bob toifa oliy
taʼlim sihat salomat sogʻliq tibbiy tibbiyot muomala qiynoq kamsit irq tenglik adolat haq haqiqat taraf maqom
munosabat tadbir chora faoliyat xizmat mablagʻ daromad hisob qayd talab murojaat ariza shikoyat mazmun maqsad
sabab holat vaziyat masala tafsil tavsif tasdiq taqdim insonparvarlik muhojir panoh qochqin ozodlik hujjat
sanʼat ijtimoiy siyosiy iqtisodiy madaniy milliy umumiy maxsus xususiy rasmiy ommaviy jamoat jamiyat
huquqbuzarlik qoidabuzarlik merosxoʻr guvohnoma bayonnoma xabarnoma iltimosnoma soʻrovnoma talabnoma vasiyatnoma
dalolatnoma ishonchnoma bildirishnoma qasd tajovuz ijro taʼsis istisno asos ixtiyor zimma qatʼ iloj imkon
qadr qimmat qadr-qimmat shafqat gʻayriinsoniy nizo ishtirok ayol jinoiy intizom intizomiy oliy harbiy irqiy
tibbiy huquqiy""".split():
    ETYM[w] = AP
for w in """konvensiya pakt protokol ratifikatsiya ratifikatsion denonsatsiya depozitariy deklaratsiya ustav statut
kodeks norma prinsip yurisdiksiya suverenitet konsul konsullik diplomat diplomatik diplomatiya delegat delegatsiya
immunitet sud sudlov ekstraditsiya ekspertiza protsessual protsedura protsess instansiya arbitraj aliment notarial
legallashtirish korrupsiya terrorizm terroristik ekstremizm separatizm transmilliy diskriminatsiya kompensatsiya
kombatant gospital lazaret sanitar sanitariya emblema rekvizitsiya repressaliy fakultativ petitsiya prokuratura
subyekt obyekt reglament kvorum komissiya assambleya qoʻmita kotibiyat tranzit internirlash deportatsiya
implementatsiya agentlik byuro federatsiya konfederatsiya respublika prezident federal mexanizm tizim standart
apparat kartochka lager signal transport ofitser komanda komandir sanksiya akkreditatsiya missiya nota
yuridik""".split():
    ETYM[w] = RU
for w in """manfaatdor taʼmin taʼminla mudofaa harakat xatti-harakat layoqat aʼzo savdo loyiha mamlakat qurbon sodir
rozi amal dushman din diniy xavf muddat barham mahrum muhokama vosita hamkorlik umumjahon vatan jabr odil imzola
alohida jarayon taomil begʻaraz ashyo doira idora nojoʻya davo davola mutlaq maʼmuriyat muntazam muayyan xodim odam
foyda foydalan ayblanuvchi himoyala himoyalan mol modda moddiy""".split():
    ETYM[w] = AP
for w in """boʻyicha ega egalik qilmish qoʻshimcha yosh atama chek chekla tuzilma belgi qarshi kurash saqla qoʻlla oshir koʻr
chiq tor buz qaytar tikla oʻt oʻta oʻti sol yasha yur joy joylashtir kech ajra qol tuga qopla ogʻir ogʻirroq sirt
kir boʻl""".split():
    ETYM[w] = UZ
for w in "zona organ gender institut gumanitar".split():
    ETYM[w] = RU

# Tarixan qo'shma so'zlar (ikki o'zakdan)
COMPOUNDS = set("xalqaro oʻzaro insonparvarlik huquqbuzarlik qoidabuzarlik merosxoʻr mansabdor".split())
COMPOUND_MARKERS = ("parvar", "buzar")
ADJ_WORDS = set("""xalqaro harbiy oliy ichki tashqi milliy umumiy maxsus xususiy rasmiy qurolli betaraf siyosiy ijtimoiy
madaniy iqtisodiy fuqaroviy huquqiy jinoiy irqiy tibbiy maʼmuriy intizomiy protsessual notarial transmilliy fakultativ
diplomatik yuridik vakolatli shaxsiy mulkiy davlatlararo oʻzaro ixtiyoriy majburiy vaqtinchalik doimiy yakuniy
asosiy zaruriy jismoniy ruhiy insoniy gʻayriinsoniy shafqatsiz adolatli qonuniy noqonuniy gʻayriqonuniy
ishtirokchi ahdlashuvchi muayyan tomonlama koʻp tomonlama manfaatdor bepul ayol muntazam odil""".split())
