<script setup>
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  ArrowDownCircleIcon,
 } from "@heroicons/vue/24/outline"

import AddToCollectionButtons from "../collections/AddToCollectionButtons.vue"
import ExportSingleItem from "./ExportSingleItem.vue"
import RelatedCollectionItem from "../collections/RelatedCollectionItem.vue"

import { httpClient } from "../../api/httpClient"
import { highlight_words_in_text } from "../../utils/utils"

import { useToast } from "primevue/usetoast"
import Image from "primevue/image"
import Dialog from 'primevue/dialog';
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>
export default {
  inject: ["eventBus"],
  props: ["dataset", "initial_item", "show_close_button"],
  data() {
    return {
      item: this.initial_item,
      loading_item: false,
      // checking_for_fulltext: false,
      // checked_for_fulltext: false,
      // fulltext_url: null,
      body_text_collapsed: true,
      show_more_button: false,
      vector_chunk_index: 0,
      show_export_dialog: false,
      show_scroll_indicator: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
    relevant_chunks() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "vector_array") || []
    },
    relevant_keyword_highlights() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "keyword_search") || []
    },
    rendering() {
      return this.dataset.schema.detail_view_rendering
    },
  },
  methods: {
    updateItemAndRendering() {
      if (!this.item || !this.item._id) return
      const that = this

      const payload = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        fields: this.dataset.schema.detail_view_rendering.required_fields,
        relevant_parts: this.item._relevant_parts,
        get_text_search_highlights: true,
        top_n_full_text_chunks: 3,
        query: this.appStateStore.selected_document_query,
        include_related_collection_items: true,
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
            // wait till more button is rendered:
            setTimeout(() => {
              that.update_show_scroll_indicator()
            }, 100)
          }, 100)

          umami.track("document_details", { title: that.rendering.title(that.item) })
        })
        .finally(function () {
          that.loading_item = false
        })
    },
    update_column_data_only() {
      if (!this.item || !this.item._id) return
      const that = this
      const payload = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        fields: [],
        relevant_parts: null,
        get_text_search_highlights: false,
        top_n_full_text_chunks: 0,
        query: null,
        include_related_collection_items: true,
      }
      httpClient
        .post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item._related_collection_items = response.data._related_collection_items
        })
    },
    // findFulltext() {
    //   const that = this
    //   const doi = this.rendering.doi(this.item)
    //   const email = "mail@luminosus.org"
    //   axios
    //     .get(`https://api.unpaywall.org/v2/${doi}?email=${email}`)
    //     .then(function (response) {
    //       that.fulltext_url = response.data.best_oa_location
    //         ? response.data.best_oa_location.url
    //         : null
    //       that.checking_for_fulltext = false
    //       that.checked_for_fulltext = true
    //     })
    //     .catch(function (error) {
    //       console.log(error)
    //       that.fulltext_url = null
    //       that.checking_for_fulltext = false
    //       that.checked_for_fulltext = true
    //     })
    //   this.checking_for_fulltext = true
    // },
    update_show_scroll_indicator() {
      const scroll_area = this.$refs.scroll_area
      const scrollable = scroll_area.scrollHeight > scroll_area.clientHeight
      const is_at_end = scroll_area.scrollTop + scroll_area.clientHeight >= scroll_area.scrollHeight
      this.show_scroll_indicator = scrollable && !is_at_end
    },
  },
  watch: {
    initial_item() {
      this.item = {...this.initial_item, ...this.appStateStore.selected_document_initial_item}
      this.item._relevant_parts = this.appStateStore.selected_document_relevant_parts
      this.checking_for_fulltext = false
      this.checked_for_fulltext = false
      this.fulltext_url = false
      this.vector_chunk_index = 0
      this.updateItemAndRendering()
    },
    body_text_collapsed() {
      this.update_show_scroll_indicator()
    },
  },
  mounted() {
    const that = this
    this.updateItemAndRendering()
    this.show_more_button = this.$refs.body_text?.scrollHeight > this.$refs.body_text?.clientHeight

    this.eventBus.on("collection_item_added", ({collection_id, class_name, is_positive, created_item}) => {
      if (created_item.dataset_id === this.item._dataset_id && created_item.item_id === this.item._id) {
        this.item._related_collection_items.push(created_item)
      }
    })
    this.eventBus.on("collection_item_removed", ({collection_id, class_name, collection_item_id}) => {
      const index = this.item._related_collection_items.findIndex((item) => item.id === collection_item_id)
      if (index !== -1) {
        this.item._related_collection_items.splice(index, 1)
      }
    })
    const scroll_area = this.$refs.scroll_area
    scroll_area.addEventListener("scroll", this.update_show_scroll_indicator)
    scroll_area.addEventListener("resize", this.update_show_scroll_indicator)
    this.update_show_scroll_indicator()
  },
}
</script>

<template>
  <div class="p-[2px] flex flex-col">

    <div class="p-[2px] flex flex-col overflow-y-auto" ref="scroll_area"
      :class="{'shadow-[inset_0_-10px_20px_-20px_rgba(0,0,0,0.3)]': show_scroll_indicator}">

      <div class="flex flex-row w-full mb-3">
        <div class="flex-1 flex min-w-0 flex-col w-full">

          <div class="flex flex-row min-w-0 mb-1">
            <img v-if="rendering ? rendering.icon(item) : false" :src="rendering.icon(item)"
              class="h-5 w-5 mr-2" />
            <p class="min-w-0 text-md font-medium leading-tight break-words text-gray-900"
              v-html="rendering ? rendering.title(item) : ''"></p>
          </div>

          <p class="mt-1 min-w-0 flex-none text-xs leading-normal break-words text-gray-500"
            v-html="rendering ? rendering.subtitle(item) : ''">
          </p>

          <p ref="body_text" class="mt-2 text-sm text-gray-700 custom-cite-style" :class="{ 'line-clamp-[12]': body_text_collapsed }"
            v-html="(rendering && rendering.body(item)) ? highlight_words_in_text(rendering.body(item), appState.selected_document_query.split(' ')) : (loading_item ? 'loading...' : '-')"></p>
          <div v-if="show_more_button" class="mt-2 text-xs text-gray-700">
            <button @click.prevent="body_text_collapsed = !body_text_collapsed" class="text-gray-500 hover:text-blue-500">
              {{ body_text_collapsed ? "Show more" : "Show less" }}
            </button>
          </div>

        </div>
        <div v-if="rendering ? rendering.image(item) : false" class="flex-none w-32 flex flex-col justify-center ml-2">
          <Image class="w-full rounded-lg shadow-md" :src="rendering.image(item)" preview />
        </div>
      </div>

      <div v-if="relevant_chunks.length" v-for="relevant_chunk in [relevant_chunks[vector_chunk_index]]" class="mt-2 rounded-md bg-gray-50 py-2 px-2">
        <div v-if="relevant_chunk.value">
          <div class="flex flex-row items-center">
            <div class="font-semibold text-gray-600 text-sm">Relevant Part in
              {{ appState.datasets[item._dataset_id].schema.object_fields[relevant_chunk.field]?.name }}{{ relevant_chunk.value?.page ? `, Page ${relevant_chunk.value.page}` : "" }}
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
            v-html="highlight_words_in_text(relevant_chunk.value.text, appState.selected_document_query.split(' '))"></div>
          <a :href="`${rendering.full_text_pdf_url(item)}#page=${relevant_chunk.value.page}`" target="_blank"
            class="mt-1 text-gray-500 text-xs">Open PDF at this page</a>
        </div>
      </div>

      <div v-for="highlight in relevant_keyword_highlights" class="mt-2 rounded-md bg-gray-50 py-2 px-2">
        <div class="font-semibold text-gray-600 text-sm">Relevant Part in
          {{ appState.datasets[item._dataset_id].schema.object_fields[highlight.field]?.name || appState.datasets[item._dataset_id].schema.object_fields[highlight.field]?.identifier }}
          <span class="text-gray-400">(based on keywords)</span>
        </div>
        <div class="mt-1 text-gray-700 text-xs" v-html="highlight.value"></div>
      </div>

      <div class="mt-2 flex flex-none flex-row">
        <button
          v-tooltip.bottom="{ value: `Export this item in different formats`, showDelay: 500 }"
          @click="show_export_dialog = true"
          class="mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
          {{ dataset.merged_advanced_options.export_button_name || "Export" }}
        </button>
        <div v-for="link in rendering ? rendering.links : []">
          <button v-if="link.url(item)"
            class="h-full mr-3 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
            <a :href="link.url(item)" target="_blank">{{ link.label }}</a>
          </button>
        </div>
      </div>

      <Dialog v-model:visible="show_export_dialog" modal :header="dataset.merged_advanced_options.export_button_name || 'Export'">
        <ExportSingleItem :dataset="dataset" :item="item">
        </ExportSingleItem>
      </Dialog>

      <div v-for="collection_item in item._related_collection_items" class="mt-3">
        <RelatedCollectionItem :collection_item="collection_item"
          @refresh_item="update_column_data_only()">
        </RelatedCollectionItem>
      </div>

    </div>

    <div class="relative mt-3 flex flex-none flex-row items-center gap-4 h-7">

      <!-- has to be here (although displayed above) because otherwise it would scroll with the content -->
      <div v-if="show_scroll_indicator" class="absolute -top-12 right-1 h-6 w-6 rounded-full bg-white text-gray-400"
        v-tooltip.left="{'value': 'Scroll down for more'}">
        <ArrowDownCircleIcon></ArrowDownCircleIcon>
      </div>

      <AddToCollectionButtons v-if="appState.collections?.length && appState.selected_app_tab !== 'collections'"
        @addToCollection="(collection_id, class_name, is_positive) =>
            appState.add_item_to_collection(
                appState.selected_document_ds_and_id,
                collection_id,
                class_name,
                is_positive,
                /*show_toast=*/false,
              )
          " @removeFromCollection="(collection_id, class_name) =>
            appState.remove_item_from_collection(
                appState.selected_document_ds_and_id,
                collection_id,
                class_name
              )
          ">
      </AddToCollectionButtons>

      <button
        v-tooltip.bottom="{ value: `Show similar ${dataset.schema.entity_name_plural} in currently selected datasets\n(based on 'meaning')`, showDelay: 500 }"
        @click="appState.show_similar_items(appState.selected_document_ds_and_id, item)"
        class="h-full flex flex-row items-center gap-2 rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <MagnifyingGlassIcon class="h-3 w-3"></MagnifyingGlassIcon> Similar Items
      </button>

      <button v-if="rendering ? rendering.url(item) : false"
        class="h-full rounded-md px-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100">
        <a :href="rendering.url(item)" target="_blank">Link</a>
      </button>

      <div class="flex-1"></div>
      <button v-if="show_close_button"
        @click="appState.close_document_details"
        class="h-full w-10 rounded-md px-2 text-gray-500 hover:bg-gray-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>

    <div class="mt-2 flex flex-row items-end" v-if="!item?._related_collection_items?.length">
      <img src="/assets/up_left_arrow.svg" class="ml-12 mr-4 pb-1 w-8" />
      <span class="text-gray-500 italic">Add to a collection to take notes and extract information!</span>
    </div>

  </div>
</template>

<style>

.custom-cite-style cite {
  font-style: normal;
  border-left: 4px solid gray;
  padding-left: 8px;
  display: block;
  margin-top: 0.5rem;
  margin-bottom: 0.6rem;
  color: gray;
}

</style>
