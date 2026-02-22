/**
 * IronVest Copyright (c) 2008-2015 by Abine, Inc. All Rights Reserved.
 *
 * This software is the confidential and proprietary information
 * of Abine, Inc. ("Confidential Information"), subject
 * to the Non-Disclosure Agreement and/or License Agreement you entered
 * into with Abine. You shall use such Confidential Information only
 * in accordance with the terms of said Agreement(s). Abine makes
 * no representations or warranties about the suitability of the
 * software. The software is provided with ABSOLUTELY NO WARRANTY
 * and Abine will NOT BE LIABLE for ANY DAMAGES resulting from
 * the use of the software.
 *
 * Contact license@getabine.com with any license-related questions.
 *
 * https://www.abine.com
 * @license
 *
 */!function(){function t(){o.className="mmFadeOut",m&&(m.style.display="none"),i&&(i.style.display="none"),l.className="";var n=[o,m,i,l];setTimeout(function(){for(var e=0;e<n.length;e++){var t=n[e];t&&t.parentNode&&t.parentNode.removeChild(t)}},2e3)}var e=window.location.href;if(window.top==window&&e.match(/dntmeFullTour=|dntmeTour=/)){var n="mmPostInstallFlow",o=document.createElement("iframe");o.style.opacity="0";var l=document.createElement("div");l.className="dntmDimPostInstall";var i=null,m=null,d={id:n,scrolling:"no",allowTransparency:"true",frameborder:"0"},s=document.documentElement.clientHeight,r=document.documentElement.clientWidth;if(-1!=e.indexOf("dntmeFullTour")){var a=e.indexOf("dntmeFullTour")+14,c=e.length-a;-1!=e.indexOf("&",a)&&(c=e.indexOf("&",a)-a),d.src=e.substr(a,c)+"?domain="+window.location.host+"&w="+r+"&h="+s,d.top=-s+"px",d.height=s+"px",d.id=n+"Full"}else d.src=e.substr(e.indexOf("dntmeTour")+10)+"?domain="+window.location.host,(i=document.createElement("div")).id="mmPostInstallArrow",i.style.display="none",(m=document.createElement("div")).innerHTML="CLOSE &nbsp;x",m.id="mmPostInstallClose",m.style.opacity="0",m.onclick=t;for(var u in d)o.setAttribute(u,d[u]);o.style.width=r+"px",i&&document.documentElement.insertBefore(i,document.documentElement.firstChild),document.documentElement.insertBefore(l,document.documentElement.firstChild),document.documentElement.insertBefore(o,l),m&&(m.style.left=r-80+"px",document.documentElement.insertBefore(m,o)),setTimeout(function(){o.className="mmFadeIn",i&&setTimeout(function(){i.style.display=""},1e3),m&&setTimeout(function(){m.className="show"},3e3)},1e3),window.addEventListener("message",function(e){0==d.src.indexOf(e.origin)&&"close"==e.data&&t()},!1)}}();