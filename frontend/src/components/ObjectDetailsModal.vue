<script setup>
import { XMarkIcon } from '@heroicons/vue/24/outline';
import axios from 'axios';

import LoadingDotAnimation from './LoadingDotAnimation.vue';
import AddToClassifierButtons from './AddToClassifierButtons.vue';

import httpClient from '../api/httpClient';
</script>

<script>

export default {
  props: ["dataset", "initial_item", "classifiers", "last_used_classifier_id"],
  emits: ["addToClassifier", "showSimilarItems", "close"],
  data() {
    return {
      rendering: null,
      item: this.initial_item,
      loading_item: false,
      checking_for_fulltext: false,
      checked_for_fulltext: false,
      fulltext_url: null,
    }
  },
  methods: {
    updateItemAndRendering() {
      if (!this.item || !this.item._id) return;
      const that = this
      const rendering = this.dataset.detail_view_rendering
      for (const field of ['title', 'subtitle', 'body', 'image', 'url', 'doi']) {
        rendering[field] = rendering[field] ? eval(rendering[field]) : ((item) => "")
      }
      that.rendering = rendering

      const payload = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        fields: this.dataset.detail_view_rendering.required_fields
      }
      this.loading_item = true
      httpClient.post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = response.data
        })
        .finally(function () {
          that.loading_item = false
        })
    },
    findFulltext() {
      const that = this
      const doi = this.rendering.doi(this.item)
      const email = "mail@luminosus.org"
      axios.get(`https://api.unpaywall.org/v2/${doi}?email=${email}`)
        .then(function (response) {
          that.fulltext_url = response.data.best_oa_location ? response.data.best_oa_location.url : null
          that.checking_for_fulltext = false
          that.checked_for_fulltext = true
        })
        .catch(function (error) {
          console.log(error);
          that.fulltext_url = null
          that.checking_for_fulltext = false
          that.checked_for_fulltext = true
        })
      this.checking_for_fulltext = true
    },
  },
  watch: {
    initial_item() {
      this.item = this.initial_item
      this.checking_for_fulltext = false
      this.checked_for_fulltext = false
      this.fulltext_url = false
      this.updateItemAndRendering()
    },
  },
  mounted() {
    this.updateItemAndRendering()
  },
}
</script>


<template>
  <div class="flex-initial flex flex-col overflow-hidden min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
    <p class="flex-none text-sm font-medium leading-6 text-gray-900"><div v-html="rendering ? rendering.title(item) : ''"></div></p>
    <p class="flex-none mt-1 text-xs leading-5 text-gray-500"><div v-html="rendering ? rendering.subtitle(item) : ''"></div></p>
    <p class="flex-1 overflow-y-auto mt-2 text-xs leading-5 text-gray-700"
      v-html="loading_item ? 'loading...' : (rendering ? rendering.body(item) : null)"></p>
    <div>
      <img v-if="rendering ? rendering.image(item) : false" class="flex-none h-52" :src="rendering ? rendering.image(item) : null">
    </div>
    <div class="flex-none flex flex-row mt-2">
      <AddToClassifierButtons :classifiers="classifiers" :last_used_classifier_id="last_used_classifier_id"
        @addToClassifier="(classifier_id, class_name, is_positive) => $emit('addToClassifier', classifier_id, class_name, is_positive)">
      </AddToClassifierButtons>
      <button @click="$emit('showSimilarItems')" class="px-3 mr-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        Show Similar Items
      </button>

      <button v-if="(rendering ? rendering.url(item) : false)" class="px-3 mr-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        <a :href="rendering.url(item)" target="_blank">Link</a>
      </button>

      <button v-if="(rendering ? rendering.doi(item) : false) && !checking_for_fulltext && !checked_for_fulltext" @click="findFulltext" class="px-3 mr-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        Find Fulltext
      </button>
      <div v-if="checking_for_fulltext" class="h-full w-10 flex place-items-center">
        <LoadingDotAnimation></LoadingDotAnimation>
      </div>
      <button type="button" v-if="checked_for_fulltext && fulltext_url" class="px-3 mr-3 text-sm text-green-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        <a :href="fulltext_url" target="_blank">Open Fulltext</a>
      </button>
      <button disabled v-if="checked_for_fulltext && !fulltext_url" class="px-3 mr-3 text-sm text-red-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        No open access fulltext found
      </button>

      <div class="flex-1"></div>
      <button @click="$emit('close')" class="w-12 px-3 text-gray-500 hover:bg-gray-100 rounded-md">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
  </div>
</template>

<style scoped></style>
