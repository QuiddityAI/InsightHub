import axios from "axios"

function get_cookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie != '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
          var cookie = cookies[i].trim();
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) == (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
          }
      }
  }
  return cookieValue;
}

// from https://dev.to/localeai/architecting-http-clients-in-vue-js-applications-for-effective-network-communication-1eec

export const httpClient = axios.create({
  baseURL: "",
  headers: {
    "Content-Type": "application/json",
  },
})

export const djangoClient = axios.create({
  baseURL: "",
  headers: {
    "X-CSRFToken": get_cookie("csrftoken"),
  },
})
