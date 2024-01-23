import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import EmbedMain from './EmbedMain.vue'

const pinia = createPinia()
const app = createApp(EmbedMain)

app.use(pinia)
app.mount('#app')
