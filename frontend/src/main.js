import { createApp } from "vue"
import { createPinia } from "pinia"
import mitt from 'mitt';
import PrimeVue from 'primevue/config';
import Wind from './prime_vue_presets/wind';
import ToastService from 'primevue/toastservice';
import DialogService from 'primevue/dialogservice';
import Tooltip from 'primevue/tooltip';
import VueApexCharts from "vue3-apexcharts";
import "inter-ui/inter.css";
import {marked} from "marked";
import markedKatex from "marked-katex-extension";

import "./style.css"
import SearchAndMap from "./apps/SearchAndMap.vue"
import { get_download_url } from "./utils/utils";  // used in item rendering definitions

globalThis.get_download_url = get_download_url;

const options = {
  throwOnError: false
};

marked.use(markedKatex(options));

const pinia = createPinia()
const app = createApp(SearchAndMap)

const eventBus = mitt();
app.provide('eventBus', eventBus);

app.use(PrimeVue, {
  unstyled: true,
  pt: Wind,
});
app.use(ToastService);
app.use(DialogService);
app.directive('tooltip', Tooltip);

app.use(VueApexCharts)

app.use(pinia)
app.mount("#app")
