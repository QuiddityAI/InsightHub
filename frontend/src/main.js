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
import { setupI18n, setI18nLanguage, loadLocaleMessages, SUPPORT_LOCALES  } from "./i18n.js";
import message_en from "./locales/en.json";

globalThis.get_download_url = get_download_url;
globalThis.icon_for_file_suffix = icon_for_file_suffix;
globalThis.marked = marked;

const katex_options = {
  throwOnError: false
};

marked.use(markedKatex(katex_options))

const pinia = createPinia()
const app = createApp(MainApp)

const i18n = setupI18n({
  locale: 'en',
  fallbackLocale: 'en',
  silentTranslationWarn: true,
  silentFallbackWarn: true,
  messages: {
    en: message_en  // always load en in the beginning to avoid warnings
  }
})
// hacky way to make i18n available in pinia stores, but there isn't a better way apparently
globalThis.$t = i18n.global.t

const preferred_language = navigator.languages[0].split('-')[0]
if (SUPPORT_LOCALES.includes(preferred_language)) {
  loadLocaleMessages(i18n, preferred_language).then(() => {
    setI18nLanguage(i18n, preferred_language)
  })
}
app.use(i18n)

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
