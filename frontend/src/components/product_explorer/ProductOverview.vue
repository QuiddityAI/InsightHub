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
</script>

<template>

  <div class="flex flex-col gap-1">

    <div class="text-xl font-['Lexend'] font-bold text-gray-600 mt-32 w-full text-center">
      Our <span class="underline decoration-2">universal platform</span> Quiddity Engine provides
    </div>
    <div class="text-4xl font-['Lexend'] font-bold text-gray-800 mt-2 w-full text-center">
      AI search and processing <br>
      <span class="text-indigo-600">in a unique tabular format</span>
    </div>

    <div class="text-2xl font-['Lexend'] font-bold text-gray-600 mt-32 w-full text-center">
      Our curated <span class="underline decoration-2">product portfolio</span>
    </div>
    <div class="text-3xl font-['Lexend'] font-bold text-gray-800 mt-2 w-full text-center">
      Serves <span class="text-indigo-600">highly specific use cases</span>, find yours now:
    </div>

    <div class="flex flex-row flex-wrap">
      <div class="flex-1 mt-14 flex flex-col gap-7 w-1/3 min-w-[320px] max-w-none px-3" v-for="catgeory in products">
        <div class="text-md font-medium text-gray-500 uppercase tracking-wider pb-2 -mb-2 pl-2 border-b text-center">
          {{ catgeory.category }}
        </div>
        <ProductCard v-for="product in catgeory.products" :product="product" />
      </div>
    </div>
  </div>

</template>
