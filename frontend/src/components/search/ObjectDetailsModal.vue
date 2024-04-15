<script setup>
import { XMarkIcon } from "@heroicons/vue/24/outline"
import axios from "axios"

import LoadingDotAnimation from "./LoadingDotAnimation.vue"
import AddToCollectionButtons from "../collections/AddToCollectionButtons.vue"

import { httpClient } from "../../api/httpClient"
import { highlight_words_in_text } from "../../utils/utils"

import { useToast } from "primevue/usetoast"
import Image from "primevue/image"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
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
      body_text_collapsed: true,
      show_more_button: false,
      vector_chunk_index: 0,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    relevant_chunks() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "vector_array") || []
    },
    relevant_keyword_highlights() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "keyword_search") || []
    },
  },
  methods: {
    updateItemAndRendering() {
      if (!this.item || !this.item._id) return
      const that = this
      const rendering = this.dataset.detail_view_rendering
      for (const field of ["title", "subtitle", "body", "image", "url", "doi", "icon", "full_text_pdf_url"]) {
        // eval?.('"use strict"; ' + code) prevents access to local variables and
        // any new variable or function declarations are scoped instead of global
        // (still a major security risk, more meant to prevent accidental bugs)
        rendering[field] = rendering[field] ? eval?.('"use strict"; ' + rendering[field]) : (item) => ""
      }
      for (const link of rendering.links || []) {
        link.url = link.url ? eval(link.url) : ""
      }
      that.rendering = rendering

      const payload = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        fields: this.dataset.detail_view_rendering.required_fields,
        relevant_parts: this.item._relevant_parts,
        top_n_full_text_chunks: 3,
        query: this.mapStateStore.map_parameters?.search.all_field_query,
      }
      this.loading_item = true
      httpClient
        .post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = {
            ...that.item,
            ...response.data
          }
          // height of text is only available after rendering:
          setTimeout(() => {
            that.show_more_button = that.$refs.body_text?.scrollHeight > that.$refs.body_text?.clientHeight
          }, 100)
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
    this.show_more_button = this.$refs.body_text?.scrollHeight > this.$refs.body_text?.clientHeight
  },
}
</script>

<template>
  <div class="overflow-scroll max-h-[90vh] rounded-md bg-white p-3 shadow-sm w-full">
    <div class="flex flex-row w-full">
      <div class="flex-1 flex min-w-0 flex-col w-full">

        <div>
          <img v-if="rendering ? rendering.icon(item) : false" :src="rendering.icon(item)"
            class="h-5 w-5 mr-2 inline" />
          <p class="flex-none text-sm font-medium leading-6 text-gray-900 inline"
            v-html="rendering ? rendering.title(item) : ''"></p>
        </div>
        <p class="mt-1 flex-none text-xs leading-5 text-gray-500" v-html="rendering ? rendering.subtitle(item) : ''">
        </p>

        <p ref="body_text" class="mt-2 text-xs text-gray-700" :class="{ 'line-clamp-[12]': body_text_collapsed }"
          v-html="loading_item ? 'loading...' : rendering ? highlight_words_in_text(rendering.body(item), mapState.map_parameters?.search.all_field_query.split(' ')) : null"></p>
        <div v-if="show_more_button" class="mt-2 text-xs text-gray-700">
          <button @click.prevent="body_text_collapsed = !body_text_collapsed" class="text-gray-500">
            {{ body_text_collapsed ? "Show more" : "Show less" }}
          </button>
        </div>

      </div>
      <div v-if="rendering ? rendering.image(item) : false" class="flex-none w-32 flex flex-col justify-center ml-2">
        <Image class="w-full rounded-lg shadow-md" :src="rendering.image(item)" preview />
      </div>
    </div>

    <div v-if="relevant_chunks.length" v-for="relevant_chunk in [relevant_chunks[vector_chunk_index]]" class="mt-2 rounded-md bg-gray-100 py-2 px-2">
      <div v-if="relevant_chunk.value">
        <div class="flex flex-row items-center">
          <div class="font-semibold text-gray-600 text-sm">Relevant Part in
            {{ appState.datasets[item._dataset_id].object_fields[relevant_chunk.field]?.description }}, Page {{ relevant_chunk.value?.page }}
            <span class="text-gray-400">(based on meaning)</span>
          </div>
          <div class="flex-1"></div>
          <div v-if="relevant_chunks.length > 1" class="flex flex-row items-center">
            <button class="mr-1 rounded-md px-1 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100"
              @click="vector_chunk_index = (vector_chunk_index - 1 + relevant_chunks.length) % relevant_chunks.length">
              &lt;</button>
            <span class="text-gray-500 text-xs">
              {{ vector_chunk_index + 1 }} / {{ relevant_chunks.length }}
            </span>
            <button class="ml-1 rounded-md px-1 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100"
              @click="vector_chunk_index = (vector_chunk_index + 1) % relevant_chunks.length">
              &gt;</button>
          </div>
        </div>
        <div class="mt-1 text-gray-700 text-xs"
          v-html="highlight_words_in_text(relevant_chunk.value.text, mapState.map_parameters.search.all_field_query.split(' '))"></div>
        <a :href="`${rendering.full_text_pdf_url(item)}#page=${relevant_chunk.value.page}`" target="_blank"
          class="mt-1 text-gray-500 text-xs">Open PDF at this page</a>
      </div>
    </div>

    <div v-for="highlight in relevant_keyword_highlights" class="mt-2 rounded-md bg-gray-100 py-2 px-2">
      <div class="font-semibold text-gray-600 text-sm">Relevant Part in
        {{ appState.datasets[item._dataset_id].object_fields[highlight.field].description || appState.datasets[item._dataset_id].object_fields[highlight.field].identifier }}
        <span class="text-gray-400">(based on keywords)</span>
      </div>
      <div class="mt-1 text-gray-700 text-xs" v-html="highlight.value"></div>
    </div>

    <div class="mt-2 flex flex-none flex-row">
      <div v-for="link in rendering ? rendering.links : []">
        <button v-if="link.url(item)"
          class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
          <a :href="link.url(item)" target="_blank">{{ link.label }}</a>
        </button>
      </div>
    </div>

    <div class="mt-2 flex flex-none flex-row">
      <AddToCollectionButtons v-if="appState.collections?.length" class="mr-3" @addToCollection="(collection_id, class_name, is_positive) =>
              $emit('addToCollection', collection_id, class_name, is_positive)
            " @removeFromCollection="(collection_id, class_name) =>
              $emit('removeFromCollection', collection_id, class_name)
            ">
      </AddToCollectionButtons>
      <button
        v-if="appState.dev_mode"
        @click="toast.add({ severity: 'info', summary: 'Under construction', detail: 'This feature is currently under construction.' })"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        Similar Items
      </button>

      <button v-if="rendering ? rendering.url(item) : false"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <a :href="rendering.url(item)" target="_blank">Link</a>
      </button>

      <button v-if="(rendering ? rendering.doi(item) : false) &&
            !checking_for_fulltext &&
            !checked_for_fulltext
            " @click="findFulltext"
        class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        Find Fulltext
      </button>
      <div v-if="checking_for_fulltext" class="flex h-full w-10 place-items-center">
        <LoadingDotAnimation></LoadingDotAnimation>
      </div>
      <button type="button" v-if="checked_for_fulltext && fulltext_url"
        class="mr-3 rounded-md px-3 text-sm text-green-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <a :href="fulltext_url" target="_blank">Open Fulltext</a>
      </button>
      <button disabled v-if="checked_for_fulltext && !fulltext_url"
        class="mr-3 rounded-md px-3 text-sm text-red-500 ring-1 ring-gray-300 hover:bg-blue-100">
        No open access fulltext found
      </button>

      <div class="flex-1"></div>
      <button @click="$emit('close')" class="w-10 rounded-md px-2 text-gray-500 hover:bg-gray-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
  </div>
</template>

<style scoped></style>
