"""Conservative contracts derived from actual CSV syntax, not prose reversal."""
import re
from collections import Counter
def signature(text):
    # Actual CSV plural macros embed a numeric selector token inside braces.
    # Branch prose may be localized; selector identity and branch arity may not.
    plural_pattern=r'\{p:(\{[^{}]*\}|[^,{}]+),([^{}]*)\}'
    plurals=re.findall(plural_pattern,text)
    expanded=re.sub(plural_pattern,lambda m:m.group(1),text)
    return {
        'commands': re.findall(r'\[[^\]\r\n]*\]',text),
        'arguments': dict(Counter(t for t in re.findall(r'\{[^{}]*\}',expanded) if not t.startswith('{g:'))),
        'gender_branch_counts':[len(t[3:-1].split(',')) for t in re.findall(r'\{g:[^{}]*\}',text)],
        'unparsed_braces':re.sub(r'\{[^{}]*\}','',expanded).count('{')+re.sub(r'\{[^{}]*\}','',expanded).count('}'),
        'literal_line_breaks':text.count(r'\n'),
        'line_breaks':text.count('\n'),
        'pause_runs':re.findall(r'\|+',text),
        'option_prefix':re.match(r'^[>^]+',text).group() if re.match(r'^[>^]+',text) else '',
        'plural_selectors':[selector for selector,branches in plurals],
        'plural_branch_counts':[len(branches.split(',')) for selector,branches in plurals],
    }
def differences(en,ar):
    original,candidate=signature(en),signature(ar)
    return [key for key in original if original[key]!=candidate[key]]
