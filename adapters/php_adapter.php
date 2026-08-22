<?php
[$v,$op,$loc,$a,$z]=array_pad(array_slice($argv,1),5,'');$x=base64_decode($a);$y=$z!==''?base64_decode($z):'';
function out($a){echo json_encode($a,JSON_UNESCAPED_UNICODE);}
if($v==='normalizer'){$n1=Normalizer::normalize($x,Normalizer::FORM_C);$n2=Normalizer::normalize($y,Normalizer::FORM_C);if($op==='normalize_lower_compare'){$n1=mb_strtolower($n1,'UTF-8');$n2=mb_strtolower($n2,'UTF-8');}out(['status'=>'ok','kind'=>'bool','value'=>$n1===$n2,'effective_locale'=>'root']);}
elseif($v==='collator'){$c=new Collator($loc);$c->setStrength(Collator::PRIMARY);$c->setAttribute(Collator::NORMALIZATION_MODE,Collator::ON);$r=$c->compare($x,$y);out(['status'=>'ok','kind'=>$op==='compare_relation'?'int':'bool','value'=>$op==='compare_relation'?($r<=>0):$r===0,'effective_locale'=>$c->getLocale(Locale::VALID_LOCALE)]);}
else{$r=$op==='lower'?mb_strtolower($x,'UTF-8'):mb_strtoupper($x,'UTF-8');out(['status'=>'ok','kind'=>'string','value_b64'=>base64_encode($r),'effective_locale'=>'root']);}
?>
