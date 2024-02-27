import { createApp } from "vue"
import { createPinia } from "pinia"
import mitt from 'mitt';
import PrimeVue from 'primevue/config';
import Wind from './prime_vue_presets/wind';
import ToastService from 'primevue/toastservice';
import VueApexCharts from "vue3-apexcharts";
import "inter-ui/inter.css";

import "./style.css"
import SearchAndMap from "./apps/SearchAndMap.vue"

const pinia = createPinia()
const app = createApp(SearchAndMap)

const eventBus = mitt();
app.provide('eventBus', eventBus);

app.use(PrimeVue, {
  unstyled: true,
  pt: Wind,
});
app.use(ToastService);

app.use(VueApexCharts)

app.use(pinia)
app.mount("#app")
