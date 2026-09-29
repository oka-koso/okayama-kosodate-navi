(()=>{
  function init(){
    const menuBtn=document.querySelector(".site-menu-button");
    const nav=document.querySelector(".site-main-nav");
    if(menuBtn&&nav){
      const close=()=>{menuBtn.setAttribute("aria-expanded","false");nav.classList.remove("is-open")};
      document.addEventListener("keydown",e=>{if(e.key==="Escape")close()});
      document.addEventListener("click",e=>{
        if(menuBtn.getAttribute("aria-expanded")==="true"&&!menuBtn.contains(e.target)&&!nav.contains(e.target))close();
      });
    }

    if(!document.querySelector(".back-to-top")){
      const b=document.createElement("button");
      b.type="button"; b.className="back-to-top"; b.setAttribute("aria-label","ページ上部へ戻る");
      b.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 14.5 12 8.5l6 6"/></svg>';
      document.body.appendChild(b);
      const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
      const update=()=>b.classList.toggle("is-visible",window.scrollY>520);
      addEventListener("scroll",update,{passive:true}); update();
      b.addEventListener("click",()=>window.scrollTo({top:0,behavior:reduce?"auto":"smooth"}));
    }
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();