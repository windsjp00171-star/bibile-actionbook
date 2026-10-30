// 頁首的晨光剖面線稿：每個瀏覽工作階段第一次看到才播繪製動畫，之後換頁直接顯示完成畫面。
(function () {
  document.querySelectorAll('.sa[data-sa-once]').forEach(function (el) {
    var seen = false;
    try { seen = sessionStorage.getItem('bible-art-played') === '1'; } catch (e) {}
    if (seen) return;
    el.classList.add('play');
    try { sessionStorage.setItem('bible-art-played', '1'); } catch (e) {}
  });
})();
