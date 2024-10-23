import { createApp } from "vue"
import { createPinia } from "pinia"
import mitt from 'mitt';
import PrimeVue from 'primevue/config';
//import Wind from './prime_vue_presets/wind';
import Aura from './prime_vue_presets/aura';
import ToastService from 'primevue/toastservice';
import DialogService from 'primevue/dialogservice';
import Tooltip from 'primevue/tooltip';
import VueApexCharts from "vue3-apexcharts";
import "inter-ui/inter.css";
import {marked} from "marked";
import markedKatex from "marked-katex-extension";

import "./style.css"
import MainApp from "./apps/MainApp.vue"
import { get_download_url, icon_for_file_suffix } from "./utils/utils";  // used in item rendering definitions
import { useAppStateStore } from "./stores/app_state_store";
import { useCollectionStore } from "./stores/collection_store";

globalThis.get_download_url = get_download_url;
globalThis.icon_for_file_suffix = icon_for_file_suffix;

const katex_options = {
  throwOnError: false
};

marked.use(markedKatex(katex_options))

const pinia = createPinia()
const app = createApp(MainApp)

const eventBus = mitt();
window.eventBus = eventBus;
app.provide('eventBus', eventBus);

app.use(PrimeVue, {
  unstyled: true,
  pt: Aura,
});
app.use(ToastService);
app.use(DialogService);
app.directive('tooltip', Tooltip);

app.use(VueApexCharts)

app.use(pinia)
const appState = useAppStateStore()
const collectionStore = useCollectionStore()
window.appState = appState
window.collectionStore = collectionStore

app.mount("#app")

