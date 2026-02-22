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
 */!function(){function t(){r.attributes.injectedOnFocus=!0,chrome.extension.sendRequest({eventName:"injectContentScript",payload:{file:"content.js",allFrames:!0,runAt:"document_idle"}})}function n(e){if("INPUT"===e.tagName){if((e.getAttribute("type")||"text").toLowerCase()in{text:1,password:1,email:1,tel:1})return!0}else if("SELECT"===e.tagName)return!0;return!1}function i(e){n(e.target||e.srcElement)&&(document.removeEventListener("focus",i,!0),window.lastFieldFocused=e.target||e.srcElement,t())}function e(){return!(!document.activeElement||"BODY"==document.activeElement.tagName)||3<=document.querySelectorAll("input[type=text], input[type=password], input[type=number], select").length}var r=document.documentElement;if("iframe_content.js"!=r.attributes.idmeScript&&"content.js"!=r.attributes.idmeScript&&(r.attributes.idmeScript="iframe_content.js",document.defaultView!=document.defaultView.top))try{var o=window.frameElement;o.ownerDocument.location.host;if(window.top!=window.parent)throw"nested iframe cannot be process in TOP content script";r.attributes.idmeScript="content.js",o.getAttribute("id")||o.setAttribute("id","mmFrameId_"+Math.random()),chrome.extension.sendRequest({eventName:"processFormsInNewFrame",frame_id:o.getAttribute("id")})}catch(c){e()?t():document.addEventListener("focus",i,!0)}}();