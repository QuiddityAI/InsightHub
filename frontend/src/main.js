import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import SearchAndMap from './apps/SearchAndMap.vue'

const pinia = createPinia()
const app = createApp(SearchAndMap)

app.use(pinia)
app.mount('#app')
