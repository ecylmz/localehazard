#define _GNU_SOURCE
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <stdlib.h>
void m1(char *); void l1(char *); void m2(wchar_t *); void l2(wchar_t *); void m3(char *); void l3(char *);
int m4(const char*, const char*); int l4(const char*, const char*); void m5(const char **, size_t); void l5(const char **, size_t);
static void o(const char*p,const char*r,int ok){printf("c\t%s\t%s\t%s\n",p,r,ok?"CORRECT":"CDM");}
static int bc(const void*a,const void*b){return strcmp(*(const char*const*)a,*(const char*const*)b);}
int main(void){
  if(!setlocale(LC_ALL,"tr_TR.UTF-8")){fprintf(stderr,"no tr locale\n");return 2;}
  char a[]="TITLE"; m1(a); o("P1","machine",!strcmp(a,"title"));
  char b[]="I\xc5\x9eIK"; l1(b); o("P1","linguistic",!strcmp(b,"\xc4\xb1\xc5\x9f\xc4\xb1k"));
  wchar_t c[]=L"TITLE"; m2(c); o("P2","machine",!wcscmp(c,L"title"));
  wchar_t d[]=L"IŞIK"; l2(d); o("P2","linguistic",!wcscmp(d,L"ışık"));
  char e[]="TITLE"; m3(e); o("P3","machine",!strcmp(e,"title"));
  char f[]="I\xc5\x9eIK"; l3(f); o("P3","linguistic",!strcmp(f,"\xc4\xb1\xc5\x9f\xc4\xb1k"));
  o("P4","machine",m4("FILE","file"));
  o("P4","linguistic",l4("I\xc5\x9eIK","\xc4\xb1\xc5\x9f\xc4\xb1k") && !l4("ISIK","\xc4\xb1\xc5\x9f\xc4\xb1k"));
  const char *k[]={"cam","\xc3\xa7" "ay","da\xc4\x9f","Zeta","alpha","\xc4\xb0zmir","\xc4\xb1rmak","ilk"}; const char *bw[8]; memcpy(bw,k,sizeof k);
  m5(k,8); qsort(bw,8,sizeof *bw,bc); int same=1; for(int i=0;i<8;i++) if(strcmp(k[i],bw[i])) same=0; o("P5","machine",same);
  const char *n[]={"da\xc4\x9f","\xc3\xa7" "ay","cam"}; l5(n,3); o("P5","linguistic",!strcmp(n[0],"cam")&&!strcmp(n[1],"\xc3\xa7" "ay")&&!strcmp(n[2],"da\xc4\x9f"));
  return 0; }
