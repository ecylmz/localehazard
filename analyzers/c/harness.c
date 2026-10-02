#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <stdlib.h>
void header_key(char *); void config_key(wchar_t *); int is_keyword(const char*, const char*); void sort_index_keys(const char **, size_t);
static void o(const char*p,const char*r,int ok){printf("c\t%s\t%s\t%s\n",p,r,ok?"CORRECT":"CDM");}
static int bcmp_(const void*a,const void*b){return strcmp(*(const char*const*)a,*(const char*const*)b);}
int main(void){
  if(!setlocale(LC_ALL,"tr_TR.UTF-8")){fprintf(stderr,"no tr locale\n");return 2;}
  char h[]="TITLE"; header_key(h); o("P1","machine",strcmp(h,"title")==0);
  /* P1 linguistic: byte-wise tolower cannot map multibyte UTF-8 Turkish letters */
  wchar_t w[]=L"TITLE"; config_key(w); o("P2","machine",wcscmp(w,L"title")==0);
  o("P4","machine",is_keyword("FILE","file"));
  const char *k[]={"cam","\xc3\xa7" "ay","da\xc4\x9f","Zeta","alpha","\xc4\xb0zmir","\xc4\xb1rmak","ilk"}; const char *b[8]; memcpy(b,k,sizeof k);
  sort_index_keys(k,8); qsort(b,8,sizeof *b,bcmp_); int same=1; for(int i=0;i<8;i++) if(strcmp(k[i],b[i])) same=0; o("P5","machine",same);
  return 0; }
