<script setup>
import { ref, computed, watch, inject, onMounted } from 'vue';
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
import ProductOverview from './ProductOverview.vue';
import ProductDetails from './ProductDetails.vue';

// Store initialization
const appState = useAppStateStore()
const toast = useToast()
const eventBus = inject('eventBus')

watch(() => appState.product_slug, (newVal) => {
  // scroll to top:
  document.getElementById('product-explorer').scrollTo(0, 0)
})

onMounted(() => {
  document.title = "Quiddity Products"
})
</script>

<template>
  <div class="relative bg-gray-100 overflow-y-auto pb-20" id="product-explorer">
    <button @click="appState.hide_product_explorer()" class="absolute top-3 right-3 z-50">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <div class="max-w-[1024px] mx-auto flex flex-col gap-1 pt-5">

      <nav class="shadow-lg rounded-xl h-14 bg-white flex flex-row items-center pl-4 pr-4 gap-3">

        <img class="h-11" src="/assets/quiddity_logo.png" alt="Quiddity Logo">

        <span class="font-['Lexend'] font-bold text-2xl text-gray-800">
          Quiddity
        </span>

        <div class="flex-1"></div>

        <a class="bg-indigo-600 text-white px-4 py-1 rounded-lg shadow-md hover:bg-indigo-500 transition-[background-color] duration-200"
          href="https://quiddityai.com/">
          Back to Company Page ▲
        </a>
      </nav>

      <ProductOverview v-if="!appState.product_slug" />

      <ProductDetails v-if="appState.product_slug" :product_slug="appState.product_slug" />

    </div>


  </div>
</template>
