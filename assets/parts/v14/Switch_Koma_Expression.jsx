#target photoshop
/* 羽月こま v14: one-expression-at-a-time selector. No save, export or network. */
(function () {
    if (!app.documents.length) { alert('先に koma_expression_collection_v14.psd を開いてください。'); return; }
    var doc = app.activeDocument;
    var folders = [];
    for (var i = 0; i < doc.layerSets.length; i++) {
        if (doc.layerSets[i].name.indexOf('EXP ') === 0) folders.push(doc.layerSets[i]);
    }
    folders.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
    if (folders.length !== 7) { alert('v14 の EXP フォルダーが 7 個見つかりません。対象 PSD を確認してください。'); return; }
    var labels = ['00 Neutral | 通常（元の表情）'];
    for (var j = 0; j < folders.length; j++) labels.push(folders[j].name.substring(4));
    var win = new Window('dialog', '羽月こま・表情切り替え');
    win.orientation = 'column'; win.alignChildren = 'fill';
    win.add('statictext', undefined, '表情を 1 つ選択します。元の目・口の開閉は通常状態に戻します。');
    var picker = win.add('dropdownlist', undefined, labels); picker.selection = 0;
    var buttons = win.add('group'); buttons.alignment = 'right';
    buttons.add('button', undefined, 'キャンセル', {name:'cancel'});
    buttons.add('button', undefined, '切り替え', {name:'ok'});
    if (win.show() !== 1) return;
    // Validate inherited feature layers before changing anything.
    var originals = [], roots = ['eye_screen_left','eye_screen_right','mouth'];
    for (var k = 0; k < roots.length; k++) {
        try { originals.push([doc.artLayers.getByName(roots[k]+'.open'), doc.artLayers.getByName(roots[k]+'.closed')]); }
        catch(e) { alert('元の表情レイヤーが見つからないため、変更しませんでした。'); return; }
    }
    for (var f = 0; f < folders.length; f++) folders[f].visible = false;
    for (var q = 0; q < originals.length; q++) { originals[q][0].visible = true; originals[q][1].visible = false; }
    if (picker.selection.index > 0) folders[picker.selection.index - 1].visible = true;
})();
