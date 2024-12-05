<script setup>
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  ArrowDownCircleIcon,
 } from "@heroicons/vue/24/outline"

import AddToCollectionButtons from "../collections/AddToCollectionButtons.vue"
import ExportSingleItem from "./ExportSingleItem.vue"
import RelatedCollectionItem from "../collections/RelatedCollectionItem.vue"
import ExpandableTextArea from "../widgets/ExpandableTextArea.vue"
import RelevantPartsKeyword from "./RelevantPartsKeyword.vue"
import RelevantPartsVector from "./RelevantPartsVector.vue"

import { httpClient } from "../../api/httpClient"
import { highlight_words_in_text } from "../../utils/utils"

import { useToast } from "primevue/usetoast"
import Image from "primevue/image"
import Dialog from 'primevue/dialog';
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
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
      show_export_dialog: false,
      show_scroll_indicator: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
    ...mapStores(useCollectionStore),
    relevant_keyword_highlights() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "keyword_search") || []
    },
    relevant_chunks() {
      return this.item?._relevant_parts?.filter((part) => part.origin === "vector_array") || []
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
        get_text_search_highlights: false,
        top_n_full_text_chunks: 0,
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
            that.update_show_scroll_indicator()
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
      this.updateItemAndRendering()
    },
  },
  mounted() {
    const that = this
    this.updateItemAndRendering()

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
    this.eventBus.on("show_table", () => {
      this.appStateStore.close_document_details()
    })
    const scroll_area = this.$refs.scroll_area
    scroll_area.addEventListener("scroll", this.update_show_scroll_indicator)
    scroll_area.addEventListener("resize", this.update_show_scroll_indicator)
    this.update_show_scroll_indicator()
  },
}
</script>

<template>
  <div class="flex flex-col h-full">

    <div class="p-[1px] flex flex-col overflow-y-auto" ref="scroll_area"
      :class="{'shadow-[inset_0_-10px_20px_-20px_rgba(0,0,0,0.3)]': show_scroll_indicator}">

      <div class="flex flex-row w-full mb-3">

        <!-- Left side (content, not image) -->
        <div class="flex-1 flex min-w-0 flex-col w-full">

          <!-- Tagline -->
          <div class="flex flex-row items-start mb-3 -mt-1" v-if="rendering.tagline(item)">
            <div class="flex-none h-full flex flex-row items-center">
              <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-6 w-6 mr-3" />
            </div>

            <div class="h-full min-w-0 flex flex-col gap-1">
              <div class="text-left text-[13px] leading-tight break-words text-gray-600"
                v-html="rendering.tagline(item)">
              </div>
              <div class="text-left text-[12px] leading-tight break-words text-gray-500"
                v-html="rendering.sub_tagline(item)">
              </div>
            </div>
          </div>

          <!-- Heading -->
          <div class="flex flex-row min-w-0 mb-1">
            <img v-if="rendering && !rendering.tagline(item) ? rendering.icon(item) : false" :src="rendering.icon(item)"
              class="h-5 w-5 mr-2" />
            <p class="min-w-0 text-[16px] font-['Lexend'] font-medium leading-tight break-words text-gray-900"
              v-html="rendering ? rendering.title(item) : ''"></p>
          </div>

          <!-- Subtitle -->
          <p class="mt-1 min-w-0 flex-none text-[13px] leading-normal break-words text-gray-500"
            v-html="rendering ? rendering.subtitle(item) : ''">
          </p>

          <!-- Body -->
          <ExpandableTextArea max_lines="12" class="mt-2 custom-cite-style"
            :html_content="(rendering && rendering.body(item)) ? highlight_words_in_text(rendering.body(item), appState.selected_document_query.split(' ')) : (loading_item ? 'loading...' : '-')" />

        </div>

        <!-- Right side (image) -->
        <div v-if="rendering ? rendering.image(item) : false" class="flex-none w-32 flex flex-col justify-center ml-2">
          <Image class="w-full rounded-lg shadow-md" image-class="rounded-lg" :src="rendering.image(item)" preview />
        </div>
      </div>

      <!-- Relevant Vector Parts -->
      <RelevantPartsVector v-if="relevant_chunks.length"
        class="my-2"
        :item="item" :highlights="relevant_chunks"
        :rendering="rendering">
      </RelevantPartsVector>

      <!-- Relevant Keyword Parts -->
      <RelevantPartsKeyword :highlights="relevant_keyword_highlights"
        class="my-2" :dataset_id="item._dataset_id">
      </RelevantPartsKeyword>

      <!-- Export & Buttons -->
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

      <!-- Collection Memberships -->
      <br>
      <hr>
      <h3 class="mt-5 text-lg font-bold">Collections</h3>
      <div v-for="collection_item in item._related_collection_items" class="mt-3">
        <RelatedCollectionItem :collection_item="collection_item"
          @refresh_item="update_column_data_only()">
        </RelatedCollectionItem>
      </div>

    </div>

    <!-- Action Buttons -->
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
        @click="collectionStore.run_search_task_similar_to_item(appState.selected_document_ds_and_id, rendering.title(item)); appState.close_document_details();"
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
