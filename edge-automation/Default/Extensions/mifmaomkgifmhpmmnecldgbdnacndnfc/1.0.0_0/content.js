//GLOBAL VAR
let ResponseBody,
  flag = false;

//GETTING USER TOKEN
const getFromStorage = async (key) => {
  const sres = await chrome.storage.sync.get(key);

  return sres[key];
};

const setToStorage = (key, data) => {
  const obj = {};
  obj[key] = data;
  chrome.storage.sync.set(obj);
};

//ERROR DIV
const createErrorDiv = (errorMessage) => {
  let appendingEle = document.getElementById("second-div-class-id");

  let emptyDiv = document.createElement("div");
  emptyDiv.setAttribute("class", "empty-div");
  emptyDiv.style.display = "block";
  emptyDiv.setAttribute("id", "empty-div-idd");
  if (document.getElementById("empty-div-idd")) {
    return;
  } else {
    appendingEle.appendChild(emptyDiv);

    let displayDiv = document.createElement("div");
    displayDiv.setAttribute("class", "display-div");
    emptyDiv.appendChild(displayDiv);

    let infoImgg = new Image();
    let imgUrr = chrome.runtime.getURL("info.svg");
    infoImgg.src = imgUrr;
    infoImgg.setAttribute("class", "img-btn");
    displayDiv.prepend(infoImgg);

    let emptyDivMessage = document.createElement("div");
    emptyDivMessage.textContent = `${errorMessage}`;
    emptyDivMessage.setAttribute("class", "empty-div-msg");
    // emptyDivMessage.setAttribute("id", "empty-div-msg-id");
    displayDiv.appendChild(emptyDivMessage);
  }
  // document.getElementById("generate-btn-text-id").textContent = "Generate";
  // document.getElementById("loading-animation-id").style.display = "none";
  // resultDiv.disabled = false;
  emptyDiv.classList.add("shaking-div");
};

//REMOVING POPUP
const removePopUp = async () => {
  const element = document.getElementById("mainPopUp");
  element.remove();

  // chrome.runtime.sendMessage({ message: "stop-convo" });
};

const sendDataToBg = (searchQuery) => {
  chrome.runtime.sendMessage({
    message: "search-occured",
    searchQuery: searchQuery,
  });
};

//PASSING DATA TO BG FOR CHAT-GPT
const getDesiredResult = async () => {
  //sta
  //TARGET ELE'S
  let targetEle = document.getElementById("generate-btn-text-id");
  let targetImg = document.getElementById("loading-animation-id");
  let msgDiv = document.getElementById("empty-div-id");
  let inputDiv = document.getElementById("input-field-user-id");

  if (targetEle.textContent === "Generating") {
    targetEle.addEventListener("click", (e) => {
      e.preventDefault();
    });
    return false;
  } else {
    document.getElementById("result-div-id").textContent = " ";
    document.getElementById("cancel-btnn-id").style.display = "block";
    document.querySelectorAll("#copy-resp-id")[0].style.display = "none";
    document.getElementById("rate-main-id").style.visibility = "hidden";
  }

  let at = await getFromStorage("accessToken");

  if (at) {
    let prevConvoDiv = document.querySelectorAll(".ii.gt")?.[0];

    if (prevConvoDiv) {
      //if prev convo exists

      msgDiv.style.display = "none";

      let prevConvoDivData;
      let query = inputDiv.value;
      if (query.includes("Write a mail/reply that..") && prevConvoDiv.textContent.length <=10 ) {
        msgDiv.style.display = "block";
        msgDiv.classList.add("shaking-div"); 

        if (targetEle.textContent === "Generate") {
          targetEle.addEventListener("click", (e) => {
            e.preventDefault();
          });
          return false;
        } 
      } else {
        if (targetEle.textContent === "Generate") {
          targetEle.textContent = "Generating"; 
          targetImg.style.display = "inline";
        }
        let queryy;
        if(!query.includes("Write a mail/reply that..")){
          queryy = query;
        }
        else{
          queryy =  "Write a formal reply to this email"
        }
        prevConvoDivData =` ${queryy}: ${prevConvoDiv.textContent.replaceAll("\n", " ")}`  
        
        sendDataToBg(prevConvoDivData)
      
      }
    } else {
      //if prev convo doesnt exists

      if (inputDiv.value != "Write a mail/reply that..") {
        sendDataToBg(inputDiv.value);
        msgDiv.style.display = "none";
        targetEle.textContent = "Generating";
        targetImg.style.display = "inline";

      } else {
        msgDiv.style.display = "block";
        msgDiv.classList.add("shaking-div");
      }
    }
  } else {
    targetEle.addEventListener("click", (e) => {
      e.preventDefault();
    });
  }

  //end
};

//RESULT FROM CHAT-GPT
const appendingResponse = async (result) => {
  let resultDiv = document.getElementById("result-div-id");

  let resultArray = result.split(" ");

  let index = 0;

  function words() {
    let curWord = resultArray[index];
    let curLetter = curWord[0];
    let i = 1;

    function Letters() {
      resultDiv.innerHTML += curLetter;
      curLetter = curWord[i++];
      if (i <= curWord.length) {
        setTimeout(Letters, 10);
      } else {
        resultDiv.innerHTML += " ";
        index++;
        if (index === resultArray.length - 1) {
          document.getElementById("generate-btn-text-id").textContent =
            "Generate";
          document.getElementById("cancel-btnn-id").style.display = "none";
          document.getElementById("copy-resp-id").style.display =
            "inline-block";
          document.getElementById("loading-animation-id").style.display =
            "none";
          resultDiv.disabled = false;
          resultDiv.style.cursor = "auto";
          document.getElementById("rate-main-id").style.visibility = "visible";
        }
        if (index < resultArray.length) {
          setTimeout(words, 30);
        }
      }
    }

    Letters();
  }
  words();
};

// ADD TO GMAIL BODY
const addToGmail = async () => {
  document.getElementById("copy-resp-id").textContent = "Copied";
  
  resDiv = document.querySelectorAll('[aria-label="Message Body"]')?.[1];

  if (resDiv) {
    var resultArr = ResponseBody?.split("\n");
    resultArr.forEach(function (resultArr) {
      var newElement = document.createElement("div");
      if (resultArr.length != 0) {
        newElement.innerHTML = resultArr;
      } else {
        newElement.innerHTML = `<br>`;
      }
      resDiv.appendChild(newElement);
    });

    removePopUp();
  } 

    let copyText = document.getElementById("result-div-id").innerHTML;
    try {
      await navigator.clipboard.writeText(copyText);
    } catch (err) {
      // console.error("Failed to copy: ", err);
    }
  
};
//OPEN EMAIL WRITER POPUP
const openPopUp = async () => {
  let at = await getFromStorage("accessToken");

  //BG DIV
  let parentDiv = document.createElement("div");
  parentDiv.setAttribute("class", "mainDiv");
  parentDiv.setAttribute("id", "mainPopUp");
  document.body.appendChild(parentDiv);

  //PARENT POPUP
  let innerDiv = document.createElement("div");
  innerDiv.setAttribute("class", "innerD");
  parentDiv.appendChild(innerDiv);

  //CANCEL BTN
  let crossButton = new Image();
  let imgUrl = chrome.runtime.getURL("cancel.svg");
  crossButton.src = imgUrl;
  crossButton.setAttribute("class", "cancel-btn");
  innerDiv.appendChild(crossButton);
  crossButton.onclick = removePopUp;

  //POPUP LOGO
  let popUpLogo = new Image();
  let url = chrome.runtime.getURL("Group.svg");
  popUpLogo.src = url;
  popUpLogo.setAttribute("class", "popup-logo");
  innerDiv.appendChild(popUpLogo);

  //FIRST DIV - START
  let firstDiv = document.createElement("div");
  firstDiv.setAttribute("class", "first-div-class");
  innerDiv.appendChild(firstDiv);

  let describeDiv = document.createElement("div");
  describeDiv.textContent = "Briefly describe what you wish to email";
  describeDiv.setAttribute("class", "des-div");
  firstDiv.appendChild(describeDiv);

  let textDiv = document.createElement("input");
  textDiv.type = "text";
  textDiv.setAttribute("class", "input-field-user");
  textDiv.setAttribute("id", "input-field-user-id");
  textDiv.value = "Write a mail/reply that..";
  firstDiv.appendChild(textDiv);

  let emptyDiv = document.createElement("div");
  emptyDiv.setAttribute("class", "empty-div");
  emptyDiv.setAttribute("id", "empty-div-id");
  firstDiv.appendChild(emptyDiv);

  let displayDiv = document.createElement("div");
  displayDiv.setAttribute("class", "display-div");
  emptyDiv.appendChild(displayDiv);

  let infoImgg = new Image();
  let imgUrr = chrome.runtime.getURL("info.svg");
  infoImgg.src = imgUrr;
  infoImgg.setAttribute("class", "img-btn");
  displayDiv.prepend(infoImgg);

  let emptyDivMessage = document.createElement("div");
  emptyDivMessage.textContent =
    "Generate what? Can you please provide more context or specify what you would like me to generate for you?";
  emptyDivMessage.setAttribute("class", "empty-div-msg");
  emptyDivMessage.setAttribute("id", "empty-div-msg-id");
  displayDiv.appendChild(emptyDivMessage);

  //FIRST DIV - END

  //SEC DIV - START

  let secondDiv = document.createElement("div");
  secondDiv.setAttribute("class", "second-div-class");
  secondDiv.setAttribute("id", "second-div-class-id");
  innerDiv.appendChild(secondDiv);

  let describeDiv2 = document.createElement("div");
  describeDiv2.textContent = "Generated Email";
  describeDiv2.setAttribute("class", "des-div");
  secondDiv.appendChild(describeDiv2);

  let resultDiv = document.createElement("textarea");
  resultDiv.setAttribute("class", "result-div");
  resultDiv.setAttribute("id", "result-div-id");
  secondDiv.appendChild(resultDiv);
  resultDiv.disabled = true;
  resultDiv.style.cursor = "not-allowed";

  //SEC DIV - END

  //THIRD DIV - START
  let thirdParentDiv = document.createElement("div");
  thirdParentDiv.setAttribute("class", "third-parent-div-class");
  thirdParentDiv.setAttribute("id", "third-parent-div-class-id");
  innerDiv.appendChild(thirdParentDiv);
  if (!at) {
    thirdParentDiv.style.display = "block";
    thirdParentDiv.classList.add("shaking-div");
  } else {
    thirdParentDiv.style.display = "none";
  }

  let thirdDiv = document.createElement("div");
  thirdDiv.setAttribute("class", "third-div-class");
  thirdDiv.setAttribute("id", "third-div-class-id");
  thirdParentDiv.appendChild(thirdDiv);

  let infoDivFir = document.createElement("div");
  infoDivFir.setAttribute("class", "info-div-fir");
  thirdDiv.appendChild(infoDivFir);

  let infoImg = new Image();
  let imgUr = chrome.runtime.getURL("info.svg");
  infoImg.src = imgUr;
  infoImg.setAttribute("class", "img-btn");
  infoDivFir.appendChild(infoImg);

  let infoDivSec = document.createElement("div");
  infoDivSec.setAttribute("class", "info-div-sec");
  thirdDiv.appendChild(infoDivSec);

  let infoDivSecOne = document.createElement("div");
  infoDivSecOne.setAttribute("class", "info-div");
  infoDivSecOne.textContent = "Cloudflare Security check required.";
  infoDivSec.appendChild(infoDivSecOne);

  let infoDivSecTwo = document.createElement("div");
  infoDivSecTwo.setAttribute("class", "info-div");
  infoDivSec.appendChild(infoDivSecTwo);

  let first = document.createElement("div");
  first.setAttribute("class", "info-div");
  first.textContent = "Please login";
  infoDivSecTwo.appendChild(first);

  let second = document.createElement("a");
  second.href = "https://chat.openai.com/auth/login";
  second.setAttribute("class", "login-link");
  second.textContent = "chat.openai.com";
  infoDivSecTwo.appendChild(second);

  let third = document.createElement("div");
  third.setAttribute("class", "info-div");
  third.textContent = "once and come back.";
  infoDivSecTwo.appendChild(third);

  //THIRD DIV - END

  //FOURTH DIV - START
  let fourthDiv = document.createElement("div");
  fourthDiv.setAttribute("class", "fourth-div-class");
  innerDiv.appendChild(fourthDiv);

  let generateBtn = document.createElement("div");
  generateBtn.setAttribute("class", "generate-btn");
  generateBtn.setAttribute("id", "generate-btn-id");
  fourthDiv.appendChild(generateBtn);

  let generateBtnText = document.createElement("div");
  generateBtnText.setAttribute("class", "generate-btn-text");
  generateBtnText.setAttribute("id", "generate-btn-text-id");
  generateBtnText.textContent = "Generate";
  generateBtn.appendChild(generateBtnText);
  generateBtn.onclick = getDesiredResult;

  let loadingImg = new Image();
  let srcc = chrome.runtime.getURL("animation.png");
  loadingImg.src = srcc;
  loadingImg.setAttribute("class", "loading-animation");
  loadingImg.setAttribute("id", "loading-animation-id");
  generateBtn.appendChild(loadingImg);

  let cancelbtn = document.createElement("button");
  cancelbtn.setAttribute("class", "cancel-btnn");
  cancelbtn.setAttribute("id", "cancel-btnn-id");
  cancelbtn.textContent = "Cancel";
  fourthDiv.appendChild(cancelbtn);
  cancelbtn.onclick = removePopUp;

  let copyResponse = document.createElement("button");
  copyResponse.setAttribute("class", "copy-resp");
  copyResponse.setAttribute("id", "copy-resp-id");
  copyResponse.textContent = "Copy Response";
  fourthDiv.appendChild(copyResponse);
  copyResponse.onclick = addToGmail;

  let rateMainDiv = document.createElement("div");
  rateMainDiv.setAttribute("class", "rate-main");
  rateMainDiv.setAttribute("id", "rate-main-id");
  fourthDiv.appendChild(rateMainDiv);

  let rateMainHeading = document.createElement("div");
  rateMainHeading.setAttribute("class", "rate-main-head");
  rateMainHeading.setAttribute("id", "rate-main-head-id");
  rateMainHeading.textContent = "Rate Us";
  rateMainDiv.appendChild(rateMainHeading);

  let rateStarDiv = document.createElement("div");
  rateStarDiv.setAttribute("class", "rate-star-div");
  rateMainDiv.appendChild(rateStarDiv);
  rateStarDiv.onclick = function () {
    window.open(
      "https://microsoftedge.microsoft.com/addons/Microsoft-Edge-Extensions-Home",
      "_blank"
    );
  };

  let src1 = chrome.runtime.getURL("greyStar.svg");
  let rateImg1 = new Image();
  rateImg1.src = src1;
  rateImg1.setAttribute("class", "star");
  rateStarDiv.append(rateImg1);

  let rateImg2 = new Image();
  rateImg2.src = src1;
  rateImg2.setAttribute("class", "star");
  rateStarDiv.append(rateImg2);

  let rateImg3 = new Image();
  rateImg3.src = src1;
  rateImg3.setAttribute("class", "star");
  rateStarDiv.append(rateImg3);

  let rateImg4 = new Image();
  rateImg4.src = src1;
  rateImg4.setAttribute("class", "star");
  rateStarDiv.append(rateImg4);

  let rateImg5 = new Image();
  rateImg5.src = src1;
  rateImg5.setAttribute("class", "star");
  rateStarDiv.append(rateImg5);

  rateStarDiv.onmouseover = function () {
    let src = chrome.runtime.getURL("yellowStar.svg");
    rateImg1.src = src;
    rateImg2.src = src;
    rateImg3.src = src;
    rateImg4.src = src;
    rateImg5.src = src;
  };

  rateStarDiv.onmouseout = function () {
    let src = chrome.runtime.getURL("greyStar.svg");
    rateImg1.src = src;
    rateImg2.src = src;
    rateImg3.src = src;
    rateImg4.src = src;
    rateImg5.src = src;
  };
  //FOURTH DIV- END
};

//APPENDING ICON FOR POPUP
const appendIcon = (positionElement) => {
  let tableCol = document.createElement("td");
  tableCol.setAttribute("class", "tab-col-class");
  if (positionElement.querySelectorAll(".tab-col-class")[0]) {
    return;
  } else {
    positionElement.insertBefore(tableCol, positionElement.children[1]);

    generateButton = document.createElement("img");
    // generateButton.className = "GptButton";
    generateButton.src = chrome.runtime.getURL("icon128.png");
    generateButton.setAttribute("class", "gpt-btn-class");
    generateButton.setAttribute("id", "gpt-btn-id");

    document.querySelectorAll(".HE").forEach((outer) => {
      if (outer) {
        let inner = outer.querySelector(".btC");
        if (inner.querySelector("#gpt-btn-id")) {
          return;
        } else {
          tableCol.appendChild(generateButton);
        }
      }
    });

    generateButton.addEventListener("click", openPopUp);
  }
};

//LISTENERS FOR BG
chrome.runtime.onMessage.addListener(async function (
  response,
  sender,
  sendResponse
) {
  if (response.message === "answer") {
    ResponseBody = response.answer;

    await appendingResponse(response.answer);
  } else if (response.message === "error") {
    //ERROR SHOW
    // createErrorDiv(response.JSONObj.split('"')[3]);
    createErrorDiv(response.JSONObj);
    if(document.getElementById("result-div-id").innerHTML){
      document.getElementById("result-div-id").innerHTML = " "
    }
    else{
      document.getElementById("result-div-id").innerHTML = " "
      document.getElementById("result-div-id").disabled = true
      document.getElementById("result-div-id").style.cursor="not-allowed"
    }

    document.getElementById("generate-btn-text-id").textContent = "Generate";
    document.getElementById("loading-animation-id").style.display = "none";
  } else if (response.message === "session-updated") {
    let at = await getFromStorage("accessToken");

    let loginTarEle = document.getElementById("third-parent-div-class-id");

    if (loginTarEle) {
      if (at) {
        loginTarEle.style.display = "none";
      } else {
        loginTarEle.style.display = "block";
        loginTarEle.classList.add("shaking-div");
      }
    }
  } else if ((response.message = "clicked")) {
    if (!flag) {
      if (document.querySelectorAll(".mainDiv")?.[0]){
        removePopUp()
        flag= false
      }
      else{
        openPopUp();
        flag = true;
      }
      
    } else {
      if (document.querySelectorAll(".mainDiv")?.[0]) {
        removePopUp();
        flag = false;
      } else {
        openPopUp();
        flag = true;
      }
    }
  }
});

//APPENDING ELE FOR POPUP ICON
const waitUntilAppendingElementLoads = async () => {
  return await new Promise((resolve, reject) => {
    let attempt = 0;
    const interval = setInterval(() => {
      let elements = document.querySelectorAll(".HE");
      attempt++;
      let finalState = true;

      if (elements.length === 0) finalState = false;

      if (attempt === 3) {
        clearInterval(interval);
        resolve([]);
      }

      if (finalState) {
        resolve(elements);
        clearInterval(interval);
      }
    }, 500);
  });
};

const handleChange = async (ele) => {
  let outerElements = await waitUntilAppendingElementLoads();
  outerElements.forEach((outer) => {
    if (outer) {
      let inner = outer.querySelector(".btC");
      appendIcon(inner);
    }
  });
};

const tillBodyLoads = async () => {
  return await new Promise((resolve, reject) => {
    const interval = setInterval(() => {
      let element = document.querySelector(".aAU");

      let finalState = true;

      if (!element) finalState = false;

      if (finalState) {
        resolve(element);
        clearInterval(interval);
      }
    }, 500);
  });
};

async function observe(cb) {
  const observer = new MutationObserver(cb);
  const root = await tillBodyLoads();

  observer.observe(root, {
    attributes: false,
    childList: true,
    subtree: true,
  });
}

observe(handleChange);

//INITIAL
(() => {
  chrome.runtime.sendMessage({ message: "session-check" });
})();

//ON WINDOW FOCUS
window.addEventListener(
  "focus",
  () => {
    chrome.runtime.sendMessage({ message: "session-check" });
  },
  true
);

window.focus();
