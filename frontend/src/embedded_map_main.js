import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import EmbeddedMap from './apps/EmbeddedMap.vue'

const pinia = createPinia()
const app = createApp(EmbeddedMap)

app.use(pinia)
app.mount('#app')
