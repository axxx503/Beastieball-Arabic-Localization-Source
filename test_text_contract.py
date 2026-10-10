import json
from pathlib import Path
from text_contract import differences
cases=[
 ('[c_red]Hi {0}[/color]|| Yes\\nNo','[c_red]مرحبًا {0}[/color]|| نعم\\nلا',[]),
 ('Hello {0} {1}','أهلًا {1} {0}',[]),
 ('Hello {0} {0}','أهلًا {0}',['arguments']),
 ('[sprIcon,0]POW','[sprIcon,1]قوة',['commands']),
 ('[c_red]Hi[/color]','[c_blue]أهلًا[/color]',['commands']),
 ('>^Nevermind','^>لا بأس',['option_prefix']),
 ('Stop|| Wait| Go','توقّف| انتظر|| انطلق',['pause_runs']),
 ('Two\\nLines','سطران',['literal_line_breaks']),
 ('Two\nLines','سطران',['line_breaks']),
 ('{2}:{3}','{2}:{3}',[]),
 ('>^Nevermind','>^لا بأس',[]),
 ('[scale,.6]Tag[/scale]\\n{0}','[scale,.6]رمز[/scale]\\n{0}',[]),
 ('Hello {name}','مرحبًا {name}',[]),
 ('Hello {name}','مرحبًا {NAME}',['arguments']),
 ('{0play} is ready','{0} جاهز',['arguments']),
 ('{g:His,Her,Their} name is {rpg_name}','{g:اسمه,اسمها,اسمهم} {rpg_name}',[]),
 ('{g:His,Her,Their} name','{g:اسمه,اسمها}',['gender_branch_counts']),
 ('Name {rpg_name}','الاسم {rpg_name',['arguments','unparsed_braces']),
 ('{0} {p:{0},turn,turns}','{0} {p:{0},من الأدوار,من الأدوار}',[]),
 ('{0} {p:{0},turn,turns}','{0} {p:{1},من الأدوار,من الأدوار}',['arguments','plural_selectors']),
 ('{0} {p:{0},turn,turns}','{0} {p:{0},دور}',['plural_branch_counts']),
 ('{0} {p:{0},turn,turns}','{0} دور',['arguments','plural_selectors','plural_branch_counts']),
]
for en,ar,expected in cases:
    assert differences(en,ar)==expected,(en,ar,differences(en,ar),expected)
report={'cases':len(cases),'passed':len(cases),'native_rendering_verified':False}
R=Path(__file__).resolve().parent
(R/'catalog/text-contract-test.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
print(json.dumps(report))
