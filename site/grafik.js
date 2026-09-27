document.querySelectorAll('.grafik').forEach(function(g){
  var ipucu=g.querySelector('.ipucu');
  g.querySelectorAll('.sira').forEach(function(s){
    function goster(){ipucu.innerHTML=s.dataset.ipucu;ipucu.style.opacity=1;
      var r=s.getBoundingClientRect(),gr=g.getBoundingClientRect();
      var x=Math.min(Math.max(8,r.left-gr.left+r.width/2-ipucu.offsetWidth/2),gr.width-ipucu.offsetWidth-8);
      ipucu.style.left=x+'px';ipucu.style.top=(r.top-gr.top-ipucu.offsetHeight-6)+'px';}
    function gizle(){ipucu.style.opacity=0;}
    s.addEventListener('mouseenter',goster);s.addEventListener('mouseleave',gizle);
    s.addEventListener('focus',goster);s.addEventListener('blur',gizle);
    s.addEventListener('touchstart',goster,{passive:true});
  });
});
