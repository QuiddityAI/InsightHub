<script setup>
import { ref, computed, watch, inject } from 'vue';
import { useToast } from 'primevue/usetoast';
import Checkbox from 'primevue/checkbox';
import { useI18n } from 'vue-i18n';
import { mapStores } from "pinia"
const { t } = useI18n();

import BorderButton from "../widgets/BorderButton.vue"
import BorderlessButton from "../widgets/BorderlessButton.vue"

import { useAppStateStore } from "../../stores/app_state_store"

// Store initialization
const appState = useAppStateStore()
const toast = useToast()
const eventBus = inject('eventBus')

// props:
const props = defineProps({
  product: Object,
})
</script>

<template>
  <div @click="appState.select_product(product.slug)"
    class="bg-white rounded-md px-3 pt-3 pb-2 shadow-sm hover:shadow-md transition-shadow flex flex-col gap-1 cursor-pointer">
    <span class="text-sm font-semibold font-['Lexend'] text-indigo-500">
      <span class="text-gray-500">Quiddity</span> {{ product.product_name }}
    </span>
    <hr>
    <span class="text-lg font-semibold text-gray-600 mb-2 leading-tight">
      {{ product.use_case }}
    </span>

    <ul class="text-sm font-normal list-disc ml-1 text-gray-500">
      <li v-for="item in product.bullets" class="ml-3 mb-1">{{ item }}</li>
    </ul>

    <img v-if="product.video_url"
      class="mx-10 shadow-md rounded-xl mt-2 hover:opacity-50"
      src="/assets/explanation_video_preview.png"
      alt="Video Preview">

    <div class="flex flex-row gap-2 mt-3 justify-between">
      <BorderlessButton>
        Find out more
      </BorderlessButton>
      <BorderButton class="text-indigo-500 border-indigo-300">
        {{ product.cost }} ➤
      </BorderButton>
    </div>
  </div>
</template>
