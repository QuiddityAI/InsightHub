<script setup>
import {
  TrashIcon,
} from "@heroicons/vue/24/outline"

import { CollectionItemSizeMode } from "../../../utils/utils.js"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../../stores/app_state_store"
import { useCollectionStore } from "../../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  props: ["dataset_id", "item_id", "initial_item", "is_positive", "show_remove_button", "collection_item", "size_mode"],
  emits: ["remove"],
  data() {
    return {
      item: {},
      loading_item: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    rendering() {
      return this.appStateStore.datasets[this.dataset_id]?.schema.result_list_rendering
    },
    schema() {
      return this.appStateStore.datasets[this.dataset_id]?.schema
    },
    is_irrelevant_according_to_ai() {
      if (this.collection_item.relevance >= 2) {
         // overriden by user or other AI judgment
        return false
      }
      if (this.collection_item?.column_data && this.collection_item.column_data['relevance']) {
        const value = this.collection_item.column_data['relevance'].value
        if (typeof value === "object") {
          if (value.is_relevant === false) {
            return true
          }
        }
      }
      return false
    },
    is_candidate() {
      return this.collection_item.relevance >= -1 && this.collection_item.relevance <= 1
    },
    actual_size_mode() {
      if (this.is_irrelevant_according_to_ai && this.size_mode > CollectionItemSizeMode.MEDIUM) {
        return CollectionItemSizeMode.MEDIUM
      }
      return this.size_mode || CollectionItemSizeMode.FULL
    },
    original_query() {
      return this.collectionStore.collection.search_sources.find(source => source.id_hash === this.collection_item.search_source_id)?.query || ""
    },
    relevant_keyword_highlights() {
      return this.collection_item?.relevant_parts?.filter((part) => part.origin === "keyword_search") || []
    },
    relevant_chunks() {
      return this.collection_item?.relevant_parts?.filter((part) => part.origin === "vector_array") || []
    },
  },
  watch: {
    dataset_id() {
      this.init()
    },
    item_id() {
      this.init()
    },
  },
  mounted() {
    this.init()
  },
  methods: {
    init() {
      const that = this
      if (!this.dataset_id || !this.item_id) return

      if (this.initial_item && this.initial_item._dataset_id === this.dataset_id && this.initial_item._id === this.item_id) {
        this.item = this.initial_item
      }
    },
  },
}
</script>

<template>
  <div v-if="rendering && item && collection_item"
    class="h-full flex flex-col gap-1 justify-center px-2"
    :class="[
      {'opacity-60': is_irrelevant_according_to_ai, },
    ]">

    <!-- Heading -->
    <div class="flex-none flex flex-row items-start">

      <div class="min-w-0 flex-shrink flex flex-row items-start bg-gray-100 rounded-md px-[6px] py-[1px]">
        <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-4 w-4 mr-2" />
        <button class="flex-shrink min-w-0 text-left text-[12px] font-normal leading-tight break-words truncate text-gray-700 hover:underline"
          v-html="rendering.title(item)"
          @click="appState.show_document_details([dataset_id, item_id], collection_item.metadata, collection_item.relevant_parts, original_query)">
        </button>
      </div>

      <div class="flex-1"></div>
      <span v-for="badge in rendering.badges(item)?.filter(badge => badge.applies)"
        v-tooltip.bottom="{ value: badge.tooltip, showDelay: 500 }"
        class="ml-2 px-2 py-[1px] rounded-xl bg-gray-200 text-xs text-gray-500">
        {{ badge.label }}
      </span>
      <button v-if="schema?.is_group_field && item[schema.is_group_field]"
        @click="collectionStore.show_group(item._dataset_id, item._id, `Directly in ${schema?.advanced_options?.group_name || 'Group'} '${rendering.title(item)}'`)"
        class="ml-2 px-2 py-[1px] rounded-xl bg-gray-100 text-xs text-gray-500 hover:bg-gray-300">
        Open
      </button>
    </div>

    <!-- Subtitle -->
    <!-- <p v-if="actual_size_mode >= CollectionItemSizeMode.MEDIUM"
      class="mt-0 text-[13px] break-words leading-normal text-gray-500"
      v-html="rendering.subtitle(item)"></p> -->

  </div>

  <!-- Alternative if rendering doesn't work to still be able to remove the item (e.g. if its deleted in the dataset) -->
  <div v-else>
    <button v-if="show_remove_button"
        @click.stop="$emit('remove')"
        v-tooltip.right="{ value: 'Remove from this collection', showDelay: 400 }"
        class="text-sm text-gray-400 hover:text-red-600">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
  </div>

</template>
