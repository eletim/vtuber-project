#target photoshop
/* 羽月こま v19: coordinated pose selector; no save/export/network. */
(function () {
  if (!app.documents.length) { alert('先に koma_separated_body_v19.psd を開いてください。'); return; }
  var doc=app.activeDocument, folders=[];
  for (var i=0;i<doc.layerSets.length;i++) if(doc.layerSets[i].name.indexOf('EXP ')===0) folders.push(doc.layerSets[i]);
  folders.sort(function(a,b){return a.name<b.name?-1:1;});
  if(folders.length!==7){alert('v19 の EXP フォルダーが 7 個見つかりません。');return;}
  var labels=['00 通常（元の表情）'];for(var j=0;j<folders.length;j++)labels.push(folders[j].name.substring(4));
  var win=new Window('dialog','羽月こま v19 表情選択');win.orientation='column';win.alignChildren='fill';
  win.add('statictext',undefined,'選んだ表情だけ表示し、目・口を描かれた基本状態に戻します。');
  var picker=win.add('dropdownlist',undefined,labels);picker.selection=0;
  var buttons=win.add('group');buttons.alignment='right';
  buttons.add('button',undefined,'キャンセル',{name:'cancel'});buttons.add('button',undefined,'切り替え',{name:'ok'});
  if(win.show()!==1)return;
  var roots=['eye_screen_left','eye_screen_right','mouth'],original=[],head;
  try { head=doc.layerSets.getByName('01 Head and front hair | 頭・前髪'); } catch(e) { alert('v19 の有効な頭グループが見つかりません。'); return; }
  try{for(var k=0;k<roots.length;k++)original.push([head.artLayers.getByName(roots[k]+'.open'),head.artLayers.getByName(roots[k]+'.closed')]);}
  catch(e){alert('元のレイヤーが見つからないため変更しませんでした。');return;}
  var chosen=picker.selection.index?folders[picker.selection.index-1]:null;
  var changes=[], plate=null;
  if(chosen){
    for(var n=0;n<chosen.artLayers.length;n++){
      var layer=chosen.artLayers[n],name=layer.name,segments=name.split('.');
      if(name.indexOf('.face_plate.brows_cheeks')>0)plate=layer;
      if(segments.length===3&&(segments[2]==='open'||segments[2]==='closed')){
        var id=segments[0],part=segments[1];
        var opened=part==='mouth'?(id==='big_smile'||id==='surprised'):id!=='big_smile';
        changes.push([layer,segments[2]==='open'?opened:!opened]);
      }
    }
    if(changes.length!==6||!plate){alert('v19 の左右の目・口の 6 レイヤーが見つからないため変更しませんでした。');return;}
  }
  for(var f=0;f<folders.length;f++)folders[f].visible=false;
  for(var q=0;q<original.length;q++){original[q][0].visible=true;original[q][1].visible=false;}
  for(var c=0;c<changes.length;c++)changes[c][0].visible=changes[c][1];
  if(chosen){plate.visible=true;chosen.visible=true;}
})();
