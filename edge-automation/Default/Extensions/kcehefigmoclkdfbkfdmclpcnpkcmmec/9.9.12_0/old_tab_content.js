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
 */!function(){try{var e=document.documentElement;try{var t=document.createEvent("Event");t.initEvent("dntme_unload",!0,!0),document.defaultView.dispatchEvent(t)}catch(n){}delete e.attributes.idmeScript,delete ABINE_DNTME,delete require,delete define}catch(n){}chrome.extension.sendRequest({eventName:"injectContentScript",payload:{file:"content.js",allFrames:!1,runAt:"document_idle"}})}();