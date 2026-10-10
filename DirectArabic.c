// Presentation-form shaping for GameMaker's bitmap draw_text path only.
// Scribble retains its own logical Arabic model; TTF outlines are untouched.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <usp10.h>
typedef struct {WCHAR base,iso,initial,medial,final;} Form;
#include "ArabicPresentationTable.h"
static const Form* form(WCHAR c){for(unsigned i=0;i<FORM_COUNT;i++)if(forms[i].base==c)return &forms[i];return 0;}
static int mark(WCHAR c){return (c>=0x64b&&c<=0x65f)||c==0x670||(c>=0x6d6&&c<=0x6ed);}
static int previous(const WCHAR* s,int p){while(--p>=0){if(!mark(s[p]))return p;}return -1;}
static int next(const WCHAR* s,int p,int n){while(++p<n){if(!mark(s[p]))return p;}return -1;}
static int leftjoin(WCHAR c){const Form* f=form(c);return c==0x640||c==0x200d||(f&&f->initial);}
static int rightjoin(WCHAR c){const Form* f=form(c);return c==0x640||c==0x200d||(f&&f->final);}
static WCHAR mirror(WCHAR c){switch(c){case '(':return ')';case ')':return '(';case '[':return ']';case ']':return '[';case '{':return '}';case '}':return '{';case '<':return '>';case '>':return '<';default:return c;}}
__declspec(dllexport) int IsLoadingArabic(const char* text){
 static const unsigned char expected[]={0xd8,0xac,0xd8,0xa7,0xd8,0xb1,0x20,0xd8,0xa7,0xd9,0x84,0xd8,0xaa,0xd8,0xad,0xd9,0x85,0xd9,0x8a,0xd9,0x84,0x2e,0x2e,0x2e,0};
 if(!text)return 0;for(int i=0;;i++){if((unsigned char)text[i]!=expected[i])return 0;if(!expected[i])return 1;}
}
typedef struct {WCHAR in[8193],shaped[8193],out[8193];SCRIPT_ITEM items[8195];BYTE levels[8193],clusterLevels[8193];int visual[8193],start[8193],end[8193];} Work;
__declspec(dllexport) void FreeArabicUtf8(char* p){if(p)HeapFree(GetProcessHeap(),0,p);}
__declspec(dllexport) char* ShapeArabicUtf8(const char* text){
 if(!text)return 0;
 int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,0,0)-1;
 if(n<=0||n>8192)return 0;
 Work* w=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(Work));if(!w)return 0;
 char* output=0;int arabic=0;
 if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,w->in,8193))goto finish;
 for(int p=0;p<n;p++){
  // Already-presented Arabic must never pass through a second reversal.
  if((w->in[p]>=0xfb50&&w->in[p]<=0xfdff)||(w->in[p]>=0xfe70&&w->in[p]<=0xfeff))goto finish;
  if(form(w->in[p]))arabic=1;
 }
 if(!arabic)goto finish;
 int out=0;
 for(int begin=0;begin<n;){
  int limit=begin;while(limit<n&&w->in[limit]!='\n'&&w->in[limit]!='\r')limit++;
  int len=limit-begin;
  if(len){
   WCHAR* s=w->in+begin;SCRIPT_CONTROL control={0};SCRIPT_STATE state={0};int count=0;
   control.uDefaultLanguage=0x401;state.uBidiLevel=1;
   // First strong character controls paragraph embedding; numbers are weak.
   for(int j=0;j<len;j++){if(form(s[j]))break;if((s[j]>='A'&&s[j]<='Z')||(s[j]>='a'&&s[j]<='z')){state.uBidiLevel=0;break;}}
   if(FAILED(ScriptItemize(s,len,8194,&control,&state,w->items,&count)))goto finish;
   for(int j=0;j<count;j++)for(int p=w->items[j].iCharPos;p<w->items[j+1].iCharPos;p++)w->levels[p]=(BYTE)w->items[j].a.s.uBidiLevel;
   for(int p=0;p<len;p++)w->shaped[p]=s[p];
   for(int p=0;p<len;p++){
    const Form* f=form(s[p]);if(!f)continue;
    int prev=previous(s,p),following=next(s,p,len);
    int back=prev>=0&&leftjoin(s[prev])&&rightjoin(s[p]);
    int forward=following>=0&&leftjoin(s[p])&&rightjoin(s[following]);
    if(s[p]==0x644&&following>=0){
     WCHAR lig=0;switch(s[following]){case 0x622:lig=0xfef5;break;case 0x623:lig=0xfef7;break;case 0x625:lig=0xfef9;break;case 0x627:lig=0xfefb;break;}
     if(lig){w->shaped[p]=lig+(back?1:0);w->shaped[following]=0;continue;}
    }
    if(!w->shaped[p])continue;
    WCHAR glyph=back?(forward?f->medial:f->final):(forward?f->initial:f->iso);
    if(glyph)w->shaped[p]=glyph;
   }
   int clusters=0;
   for(int p=0;p<len;p++){
    if(!w->shaped[p])continue;
    WCHAR c=s[p];
    if(c==0x200c||c==0x200d||c==0x200e||c==0x200f||(c>=0x202a&&c<=0x202e)||(c>=0x2066&&c<=0x2069))continue;
    if(mark(c)&&clusters){w->end[clusters-1]=p+1;continue;}
    if(c>=0xdc00&&c<=0xdfff&&clusters){w->end[clusters-1]=p+1;continue;}
    w->start[clusters]=p;w->end[clusters]=p+1;w->clusterLevels[clusters]=w->levels[p];clusters++;
   }
   if(clusters&&FAILED(ScriptLayout(clusters,w->clusterLevels,w->visual,0)))goto finish;
   for(int j=0;j<clusters;j++){
    int k=w->visual[j];for(int p=w->start[k];p<w->end[k];p++)if(w->shaped[p])w->out[out++]=(w->clusterLevels[k]&1)?mirror(w->shaped[p]):w->shaped[p];
   }
  }
  if(limit<n)w->out[out++]=w->in[limit++];begin=limit;
 }
 w->out[out]=0;
 int bytes=WideCharToMultiByte(CP_UTF8,0,w->out,-1,0,0,0,0);
 if(bytes<=0)goto finish;
 output=HeapAlloc(GetProcessHeap(),0,bytes);
 if(output&&!WideCharToMultiByte(CP_UTF8,0,w->out,-1,output,bytes,0,0)){FreeArabicUtf8(output);output=0;}
finish:HeapFree(GetProcessHeap(),0,w);return output;
}
