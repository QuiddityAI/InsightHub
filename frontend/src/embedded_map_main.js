import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import EmbeddedMapMain from './EmbeddedMapMain.vue'

const pinia = createPinia()
const app = createApp(EmbeddedMapMain)

app.use(pinia)
app.mount('#app')
