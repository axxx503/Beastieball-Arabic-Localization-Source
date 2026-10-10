export function signature(text){
 const pluralPattern=/\{p:(\{[^{}]*\}|[^,{}]+),([^{}]*)\}/g;
 const plurals=[...text.matchAll(pluralPattern)];
 const expanded=text.replace(pluralPattern,(_,selector)=>selector);
 const tokens=expanded.match(/\{[^{}]*\}/g)||[];
 const counts={};for(const t of tokens.filter(t=>!t.startsWith('{g:')))counts[t]=(counts[t]||0)+1;
 const residual=expanded.replace(/\{[^{}]*\}/g,'');
 return {commands:text.match(/\[[^\]\r\n]*\]/g)||[],arguments:Object.fromEntries(Object.entries(counts).sort()),gender_branch_counts:tokens.filter(t=>t.startsWith('{g:')).map(t=>t.slice(3,-1).split(',').length),unparsed_braces:(residual.match(/[{}]/g)||[]).length,literal_line_breaks:text.split('\\n').length-1,line_breaks:text.split('\n').length-1,pause_runs:text.match(/\|+/g)||[],option_prefix:(text.match(/^[>^]+/)||[''])[0],plural_selectors:plurals.map(m=>m[1]),plural_branch_counts:plurals.map(m=>m[2].split(',').length)};
}
export function contractSource(row,ar,exemptions){
 const repair=exemptions.repairs[row.id],literal=exemptions.literal_labels[row.id];
 if(repair){if(repair.source_sha256!==row.source_sha256||row.en.split(repair.find).length!==2)throw Error('Stale repair '+row.id);return [row.en.replace(repair.find,repair.replace),ar];}
 if(literal){if(literal.source_sha256!==row.source_sha256||literal.source!==row.en||literal.arabic!==ar)throw Error('Invalid literal label '+row.id);return ['', ''];}
 return [row.en,ar];
}
