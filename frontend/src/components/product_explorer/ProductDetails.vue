<script setup>
import { ref, computed, watch, inject } from 'vue';
import { useToast } from 'primevue/usetoast';
import Checkbox from 'primevue/checkbox';
import { useI18n } from 'vue-i18n';
import { mapStores } from "pinia"
const { t } = useI18n();

import BorderButton from "../widgets/BorderButton.vue"
import BorderlessButton from "../widgets/BorderlessButton.vue"
import ProductCard from './ProductCard.vue';
import { products } from "./products.js"

import { useAppStateStore } from "../../stores/app_state_store"

// Store initialization
const appState = useAppStateStore()
const toast = useToast()
const eventBus = inject('eventBus')

// props
const props = defineProps({
  product_slug: String,
})

const products_flat = []
for (const category of products) {
  products_flat.push(...category.products)
}

const product = computed(() => {
  return products_flat.find(p => p.slug === props.product_slug)
})
</script>

<template>
  <div class="flex flex-col gap-1 mt-5 items-start">

    <BorderlessButton @click="appState.close_product_details()" class="mb-5 !text-lg">
      ◀ Back to All Products
    </BorderlessButton>

    <div class="flex flex-row justify-between w-full mt-10 items-end">
      <div class="text-3xl font-['Lexend'] font-bold text-left text-indigo-500 border-b">
        <span class="text-gray-500">Quiddity</span> {{ product.product_name }}
      </div>
      <BorderButton class="text-indigo-500 text-xl border-indigo-300">
        {{ product.cost }} ➤
      </BorderButton>
    </div>
    <div class="text-4xl font-['Lexend'] font-bold text-gray-800 mt-2 w-full text-left">
      {{ product.use_case }}
    </div>

    <ul class="text-lg font-normal list-disc ml-1 text-gray-500 mt-5">
      <li v-for="item in product.bullets" class="ml-3 mb-1">{{ item }}</li>
    </ul>

    <div class="text-xl font-semibold text-gray-600 mt-2 w-full text-left">
      {{ product.description }}
    </div>

    <div class="flex flex-row justify-center w-full mt-10">
      <img v-if="product.video_url"
        class="h-[300px] shadow-md rounded-xl hover:opacity-50"
        src="/assets/explanation_video_preview.png"
        alt="Video Preview">
    </div>

      <div class="flex flex-row justify-center w-full mt-10">
        <BorderButton class="text-indigo-500 text-xl border-indigo-300">
          Book a 15 min Meeting Now ➤
        </BorderButton>
      </div>
  </div>
</template>
