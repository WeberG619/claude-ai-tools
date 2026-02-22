const setToStorage = (key, data) => {
  const obj = {};
  obj[key] = data;
  chrome.storage.sync.set(obj);
};

const getFromStorage = async (key) => {
  const sres = await chrome.storage.sync.get(key);
  return sres[key];
};

const fetchAPIStream = async (url, config) => {
  try {
    return await fetch(url, config);
  } catch (err) {
    return Promise.reject(err);
  }
};

const uuidv4 = () => {
  return crypto.randomUUID();
};

var handleError = function (err) {
  // console.log("error", err);
  return null;
};

const getAccessToken = async () => {
  const url = "https://chat.openai.com/api/auth/session";
  const config = {
    method: "GET",
    withCredentials: true,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  };
  const response = await fetch(url, config).catch(handleError);

  if (!response.ok) {
    throw new Error();
  }

  return response.json();
};

const createConversation = async (at, query) => {
  const url = "https://chat.openai.com/backend-api/conversation";

  const config = {
    method: "POST",
    withCredentials: true,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${at}`,
    },
    body: JSON.stringify({
      action: "next",
      messages: [
        {
          id: uuidv4(),
          role: "user",
          content: {
            content_type: "text",
            parts: [query],
          },
        },
      ],
      model: "text-davinci-002-render",
      parent_message_id: uuidv4(),
    }),
  };

  let response = await fetchAPIStream(url, config);

  if (!response.ok) {
    let cErr = await response.json();

    if (typeof cErr === "object") {
      throw new Error(JSON.stringify(cErr));
      // throw new Error(cErr.detail);
    } else {
      throw new Error("Something went wrong");
    }
  }

  return response;
};

function transform(s) {
  return JSON.parse(s.split("data: ")[1]);
}

const main = async (query) => {
  let res;
  try {
    let at = await getFromStorage("accessToken");

    if (!at) {
      // console.log("UNAUTHORIZED");
      return {};
    }

    let response = await createConversation(at, query);

    const reader = response.body
      .pipeThrough(new TextDecoderStream())
      .getReader();
    let finalStr = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) break;

      if (!value.includes("[DONE]")) finalStr = value;
    }

    let JSONObj = transform(finalStr);
    res = JSONObj;
  } catch (err) {
    res = err.message;
  }
  return res;
};

const sessionCheckAndSet = async () => {
  try {
    let userObj = await getAccessToken();

    let at = userObj.hasOwnProperty("accessToken")
      ? userObj["accessToken"]
      : "";

    await setToStorage("accessToken", at);
  } catch (err) {
    await setToStorage("accessToken", "");
  }
};

(async () => {
  await sessionCheckAndSet();
})();

chrome.runtime.onMessage.addListener(async function (
  response,
  sender,
  sendResponse
) {
  const { message } = response;
  const tabId = sender.tab.id;

  if (message === "search-occured") {
    let query = response.searchQuery;

    let JSONObj = await main(query);

    if (typeof JSONObj === "string") {
      chrome.tabs.sendMessage(tabId, { message: "error", JSONObj });
    } else {
      let answer = JSONObj?.message?.content?.parts?.[0];
      chrome.tabs.sendMessage(tabId, { message: "answer", answer });
    }
  } else if (message === "session-check") {
    await sessionCheckAndSet();

    chrome.tabs.sendMessage(tabId, { message: "session-updated" });
  }
});

chrome.runtime.onInstalled.addListener(function (details) {
  if (details.reason == "install") {
    const logo = chrome.runtime.getURL("icon128.png");

    chrome.notifications.create(
      "name-for-notification",
      {
        type: "basic",
        iconUrl: logo,
        title: "ChatGPT AI Email Writer",
        message: "Effortlessly Write Emails with ChatGPT AI Email Writer",
      },

      function () {}
    );
  }
});


//LISTENER ON BROSWER-ACTION CLICK
chrome.action.onClicked.addListener(function (tab) {
  const PageId = tab.id;
   chrome.tabs.sendMessage(PageId, { message: "clicked" });
})


 
