import axios from 'axios';

// from https://dev.to/localeai/architecting-http-clients-in-vue-js-applications-for-effective-network-communication-1eec

const httpClient = axios.create({
    baseURL: "http://localhost:55123",
    headers: {
        "Content-Type": "application/json",
    }
});

export default httpClient;