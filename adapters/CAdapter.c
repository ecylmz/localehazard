#define _GNU_SOURCE
#include <ctype.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unicode/ucol.h>
#include <unicode/ustring.h>
#include <unicode/unorm2.h>

static void fail(const char *msg) { printf("{\"status\":\"error\",\"error\":\"%s\"}\n", msg); exit(0); }
static char *b64decode(const char *src, size_t *outlen) {
  static const signed char T[256] = {
    ['A']=0,['B']=1,['C']=2,['D']=3,['E']=4,['F']=5,['G']=6,['H']=7,['I']=8,['J']=9,['K']=10,['L']=11,['M']=12,['N']=13,['O']=14,['P']=15,
    ['Q']=16,['R']=17,['S']=18,['T']=19,['U']=20,['V']=21,['W']=22,['X']=23,['Y']=24,['Z']=25,
    ['a']=26,['b']=27,['c']=28,['d']=29,['e']=30,['f']=31,['g']=32,['h']=33,['i']=34,['j']=35,['k']=36,['l']=37,['m']=38,['n']=39,['o']=40,['p']=41,
    ['q']=42,['r']=43,['s']=44,['t']=45,['u']=46,['v']=47,['w']=48,['x']=49,['y']=50,['z']=51,['0']=52,['1']=53,['2']=54,['3']=55,['4']=56,['5']=57,['6']=58,['7']=59,['8']=60,['9']=61,['+']=62,['/']=63
  };
  size_t n=strlen(src), cap=n/4*3+3, j=0; char *out=malloc(cap); unsigned v=0; int bits=0;
  for(size_t i=0;i<n;i++){ unsigned char c=src[i]; if(c=='=') break; signed char x=T[c]; if(x==0 && c!='A') continue; v=(v<<6)|(unsigned)x; bits+=6; if(bits>=8){bits-=8; out[j++]=(char)((v>>bits)&255);} }
  out[j]='\0'; *outlen=j; return out;
}
static char *b64encode(const unsigned char *src,size_t n){ static const char *A="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"; char *o=malloc(((n+2)/3)*4+1); size_t i=0,j=0; while(i<n){unsigned a=src[i++],b=i<n?src[i++]:0,c=i<n?src[i++]:0,t=(a<<16)|(b<<8)|c; o[j++]=A[t>>18];o[j++]=A[(t>>12)&63];o[j++]=(i-1>n)?'=':A[(t>>6)&63];o[j++]=(i>n)?'=':A[t&63];} size_t m=n%3;if(m){o[j-1]='=';if(m==1)o[j-2]='=';}o[j]=0;return o;}
static UChar *toU(const char *s,int32_t *len){UErrorCode e=U_ZERO_ERROR;u_strFromUTF8(NULL,0,len,s,-1,&e);e=U_ZERO_ERROR;UChar *u=malloc((*len+1)*sizeof(UChar));u_strFromUTF8(u,*len+1,len,s,-1,&e);if(U_FAILURE(e))fail("utf8_to_uchar");return u;}
static char *fromU(const UChar *u,int32_t len){UErrorCode e=U_ZERO_ERROR;int32_t n;u_strToUTF8(NULL,0,&n,u,len,&e);e=U_ZERO_ERROR;char *s=malloc(n+1);u_strToUTF8(s,n+1,&n,u,len,&e);if(U_FAILURE(e))fail("uchar_to_utf8");return s;}
static void string_result(const char *s,const char *loc){char *b=b64encode((const unsigned char*)s,strlen(s));printf("{\"status\":\"ok\",\"kind\":\"string\",\"value_b64\":\"%s\",\"effective_locale\":\"%s\"}\n",b,loc?loc:"");free(b);}
static void bool_result(int v,const char *loc){printf("{\"status\":\"ok\",\"kind\":\"bool\",\"value\":%s,\"effective_locale\":\"%s\"}\n",v?"true":"false",loc?loc:"");}
static void int_result(int v,const char *loc){printf("{\"status\":\"ok\",\"kind\":\"int\",\"value\":%d,\"effective_locale\":\"%s\"}\n",v<0?-1:v>0?1:0,loc?loc:"");}
int main(int argc,char **argv){
  if(argc<5) { fail("args"); }
  const char *variant=argv[1],*op=argv[2],*loc=argv[3]; size_t n1,n2=0;char *s1=b64decode(argv[4],&n1);char *s2=argc>5?b64decode(argv[5],&n2):strdup("");
  if(!strcmp(variant,"libc_process")||!strcmp(variant,"ascii")){
    const char *eff=setlocale(LC_ALL,loc); if(!eff){printf("{\"status\":\"environment_unavailable\",\"error\":\"setlocale_failed\",\"effective_locale\":\"\"}\n");return 0;}
    if(!strcmp(op,"lower")||!strcmp(op,"native_lower")){char *r=strdup(s1);for(size_t i=0;i<n1;i++){unsigned char c=r[i];r[i]=!strcmp(variant,"ascii")?(c>='A'&&c<='Z'?c+32:c):(char)tolower(c);}string_result(r,eff);}
    else if(!strcmp(op,"compare_equal")||!strcmp(op,"native_compare_equal")){int eq=!strcmp(variant,"ascii")?({int z=1;size_t i;if(n1!=n2)z=0;for(i=0;z&&i<n1;i++){unsigned char a=s1[i],b=s2[i];if(a>='A'&&a<='Z')a+=32;if(b>='A'&&b<='Z')b+=32;if(a!=b)z=0;}z;}):strcasecmp(s1,s2)==0;bool_result(eq,eff);} else { fail("unsupported_op"); }
    return 0;
  }
  if(!strcmp(variant,"icu_normalizer")){
    UErrorCode e=U_ZERO_ERROR;const UNormalizer2 *norm=unorm2_getNFCInstance(&e);int32_t l1,l2;UChar *u1=toU(s1,&l1),*u2=toU(s2,&l2);int32_t c1=unorm2_normalize(norm,u1,l1,NULL,0,&e);e=U_ZERO_ERROR;UChar *a=malloc((c1+1)*2);unorm2_normalize(norm,u1,l1,a,c1+1,&e);e=U_ZERO_ERROR;int32_t c2=unorm2_normalize(norm,u2,l2,NULL,0,&e);e=U_ZERO_ERROR;UChar *b=malloc((c2+1)*2);unorm2_normalize(norm,u2,l2,b,c2+1,&e);if(!strcmp(op,"normalize_lower_compare")){int32_t ca=c1*3+8,cb=c2*3+8;UChar *la=malloc(ca*2),*lb=malloc(cb*2);e=U_ZERO_ERROR;c1=u_strToLower(la,ca,a,c1,"",&e);e=U_ZERO_ERROR;c2=u_strToLower(lb,cb,b,c2,"",&e);a=la;b=lb;}bool_result(c1==c2&&u_memcmp(a,b,c1)==0,"root");return 0;
  }
  if(!strcmp(variant,"icu_collator")){
    UErrorCode e=U_ZERO_ERROR;UCollator *c=ucol_open(loc,&e);if(U_FAILURE(e)){printf("{\"status\":\"environment_unavailable\",\"error\":\"ucol_open_failed\",\"effective_locale\":\"\"}\n");return 0;}ucol_setStrength(c,UCOL_PRIMARY);ucol_setAttribute(c,UCOL_NORMALIZATION_MODE,UCOL_ON,&e);int32_t l1,l2;UChar *u1=toU(s1,&l1),*u2=toU(s2,&l2);UCollationResult rel=ucol_strcoll(c,u1,l1,u2,l2);const char *el=ucol_getLocaleByType(c,ULOC_VALID_LOCALE,&e);if(!strcmp(op,"compare_relation"))int_result((int)rel,el);else bool_result(rel==UCOL_EQUAL,el);ucol_close(c);return 0;
  }
  if(!strcmp(variant,"icu_locale")||!strcmp(variant,"icu_root")){
    const char *use=!strcmp(variant,"icu_root")?"":loc;int32_t l;UChar *u=toU(s1,&l);UErrorCode e=U_ZERO_ERROR;int32_t cap=l*3+16;UChar *r=malloc(cap*2);int32_t out=!strcmp(op,"lower")?u_strToLower(r,cap,u,l,use,&e):u_strToUpper(r,cap,u,l,use,&e);if(U_FAILURE(e))fail("icu_case");char *s=fromU(r,out);string_result(s,*use?use:"root");return 0;
  }
  fail("variant");
}
