<script setup>
import { XMarkIcon } from "@heroicons/vue/24/outline"
import axios from "axios"

import LoadingDotAnimation from "./LoadingDotAnimation.vue"
import AddToCollectionButtons from "../collections/AddToCollectionButtons.vue"

import { httpClient } from "../../api/httpClient"

import { useToast } from "primevue/usetoast"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
const toast = useToast()
</script>

<script>
export default {
  props: ["dataset", "initial_item"],
  emits: ["addToCollection", "removeFromCollection", "showSimilarItems", "close"],
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
      if (!this.item || !this.item._id) return
      const that = this
      const rendering = this.dataset.detail_view_rendering
      for (const field of ["title", "subtitle", "body", "image", "url", "doi"]) {
        rendering[field] = rendering[field] ? eval(rendering[field]) : (item) => ""
      }
      that.rendering = rendering

      const payload = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        fields: this.dataset.detail_view_rendering.required_fields,
      }
      this.loading_item = true
      httpClient
        .post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = {
            ...that.item,
            ...response.data
          }
        })
        .finally(function () {
          that.loading_item = false
        })
    },
    findFulltext() {
      const that = this
      const doi = this.rendering.doi(this.item)
      const email = "mail@luminosus.org"
      axios
        .get(`https://api.unpaywall.org/v2/${doi}?email=${email}`)
        .then(function (response) {
          that.fulltext_url = response.data.best_oa_location
            ? response.data.best_oa_location.url
            : null
          that.checking_for_fulltext = false
          that.checked_for_fulltext = true
        })
        .catch(function (error) {
          console.log(error)
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
  <div
    class="flex min-w-0 flex-initial flex-col overflow-hidden rounded-md bg-white p-3 shadow-sm">
    <p
      class="flex-none text-sm font-medium leading-6 text-gray-900"
      v-html="rendering ? rendering.title(item) : ''"></p>
    <p
      class="mt-1 flex-none text-xs leading-5 text-gray-500"
      v-html="rendering ? rendering.subtitle(item) : ''"></p>
    <p
      class="mt-2 flex-1 overflow-y-auto text-xs leading-5 text-gray-700"
      v-html="loading_item ? 'loading...' : rendering ? rendering.body(item) : null"></p>
    <div>
      <img
        v-if="rendering ? rendering.image(item) : false"
        class="h-52 flex-none"
        :src="rendering ? rendering.image(item) : null" />
    </div>
    <div class="mt-2 flex flex-none flex-row">
      <AddToCollectionButtons
        v-if="appState.collections?.length"
        class="mr-3"
        @addToCollection="
          (collection_id, class_name, is_positive) =>
            $emit('addToCollection', collection_id, class_name, is_positive)
        "
        @removeFromCollection="
          (collection_id, class_name) =>
            $emit('removeFromCollection', collection_id, class_name)
        ">
      </AddToCollectionButtons>
      <button
        @click="toast.add({severity:'info', summary:'Under construction', detail:'This feature is currently under construction.'})"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        Similar Items
      </button>

      <button
        v-if="rendering ? rendering.url(item) : false"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <a :href="rendering.url(item)" target="_blank">Link</a>
      </button>

      <button
        v-if="
          (rendering ? rendering.doi(item) : false) &&
          !checking_for_fulltext &&
          !checked_for_fulltext
        "
        @click="findFulltext"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        Find Fulltext
      </button>
      <div v-if="checking_for_fulltext" class="flex h-full w-10 place-items-center">
        <LoadingDotAnimation></LoadingDotAnimation>
      </div>
      <button
        type="button"
        v-if="checked_for_fulltext && fulltext_url"
        class="mr-3 rounded-md px-3 text-sm text-green-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <a :href="fulltext_url" target="_blank">Open Fulltext</a>
      </button>
      <button
        disabled
        v-if="checked_for_fulltext && !fulltext_url"
        class="mr-3 rounded-md px-3 text-sm text-red-500 ring-1 ring-gray-300 hover:bg-blue-100">
        No open access fulltext found
      </button>

      <div class="flex-1"></div>
      <button
        @click="$emit('close')"
        class="w-10 rounded-md px-2 text-gray-500 hover:bg-gray-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
  </div>
</template>

<style scoped></style>
