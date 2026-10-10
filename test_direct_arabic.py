from pathlib import Path
import ctypes as C,json
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
R=Path(__file__).resolve().parent
d=C.WinDLL(str(R/'staging/DirectArabic.dll'))
d.ShapeArabicUtf8.argtypes=[C.c_char_p];d.ShapeArabicUtf8.restype=C.c_void_p
d.FreeArabicUtf8.argtypes=[C.c_void_p];d.FreeArabicUtf8.restype=None
def shape(s):
 p=d.ShapeArabicUtf8(s.encode('utf8'))
 if not p:return None
 try:return C.string_at(p).decode('utf8')
 finally:d.FreeArabicUtf8(p)
r=ArabicReshaper(configuration={'delete_harakat':False,'support_ligatures':True})
cases=['جار التحميل...','للوصول للجميع','لاتصال الإنترنت','الفرق الزائرة','طابع القوائم','تمهيدي (لا تدعم الإنجازات)','اضغط SHIFT للتفاصيل','رمز الفريق 42GMC15','النتيجة 123 / 456','لا لأ لإ لآ','العربية English 123','سطر أول\nسطر ثان','عربي (English 42) الآن','عربي [SHIFT] الآن']
for s in cases:
 expected='\n'.join(get_display(r.reshape(line)) for line in s.split('\n'))
 actual=shape(s);assert actual==expected,(s,actual,expected)
for s in ['English','42GMC15','',get_display(r.reshape('جار التحميل...'))]:assert shape(s) is None
for s in ['مُعطّل','مَرْحَبًا','أهلاً!','أهلًا 😀 بالعالم']:
 actual=shape(s);assert actual and '\ufffd' not in actual
report=dict(native_module_executed=True,reference_bidi_cases=len(cases),unchanged_or_already_shaped_cases=4,mark_or_surrogate_cases=4,cases_passed=len(cases)+8,game_launched=False,in_game_verified=False)
(R/'review/direct-arabic-tests.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
