<script setup>
import {
  TrashIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
  ArrowRightIcon,
} from "@heroicons/vue/24/outline"

import Image from "primevue/image"

import BorderlessButton from "../widgets/BorderlessButton.vue"
import ExpandableTextArea from "../widgets/ExpandableTextArea.vue"
import RelevantPartsKeyword from "../search/RelevantPartsKeyword.vue"
import RelevantPartsVector from "../search/RelevantPartsVector.vue"

import { CollectionItemSizeMode, ItemRelevance } from "../../utils/utils.js"
import { httpClient } from "../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  props: ["dataset_id", "item_id", "initial_item", "is_positive", "show_remove_button", "collection_item", "size_mode"],
  emits: [],
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
    main_relevance_influence() {
      const origins = this.item._origins
      if (!origins) return null
      // find origin.type of origins with lowest origin.rank:
      const min_rank = Math.min(...origins.filter(origin => ['vector', 'keyword'].includes(origin.type)).map((origin) => origin.rank))
      const min_rank_origins = origins.filter((origin) => origin.rank === min_rank)
      const min_rank_origin_types = min_rank_origins.map((origin) => origin.type)
      if (min_rank_origin_types.includes("vector") && min_rank_origin_types.includes("keyword")) {
        return "both"
      } else if (min_rank_origin_types.includes("vector")) {
        return "vector"
      } else if (min_rank_origin_types.includes("keyword")) {
        return "keyword"
      } else {
        return null
      }
    },
    is_irrelevant_according_to_ai() {
      if (this.collection_item.relevance <= ItemRelevance.REJECTED_BY_AI) {
         // overriden by user or other AI judgment
        return true
      }
      if (this.collection_item.relevance >= ItemRelevance.APPROVED_BY_AI) {
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
      return this.collection_item.relevance === ItemRelevance.CANDIDATE
    },
    actual_size_mode() {
      if (this.is_irrelevant_according_to_ai && this.size_mode > CollectionItemSizeMode.MEDIUM) {
        return CollectionItemSizeMode.MEDIUM
      }
      return this.size_mode || CollectionItemSizeMode.FULL
    },
    original_query() {
      // FIXME: this should use the actually used search task, not the last one
      return this.collectionStore.collection.most_recent_search_task?.settings.user_input || ""
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
      this.get_full_item()
    },
    get_full_item() {
      const that = this
      if (!this.dataset_id || !this.item_id || !this.rendering) return
      const payload = {
        dataset_id: this.dataset_id,
        item_id: this.item_id,
        fields: this.rendering.required_fields,
        relevant_parts: this.collection_item.relevant_parts,
      }
      that.loading_item = true
      httpClient.post("/data_backend/document/details_by_id", payload).then(function (response) {
        that.item = { ...that.item, ...response.data }
        if (response.data._relevant_parts) {
          that.collection_item.relevant_parts = response.data._relevant_parts
        }
        that.loading_item = false
      })
    },
  },
}
</script>

<template>
  <div v-if="rendering && item && collection_item"
    class="flex flex-col gap-3 pl-4 pr-4 mb-2 rounded-md bg-white shadow-md"
    :class="[
      actual_size_mode <= CollectionItemSizeMode.SMALL ? ['pt-2', 'pb-2'] : ['pt-4', 'pb-3'],
      {'opacity-60': is_irrelevant_according_to_ai, },
    ]">

    <div class="flex flex-row gap-2">

      <!-- Left side (content, not image) -->
      <div class="flex-1 min-w-0 flex flex-col gap-1">

        <!-- Tagline -->
        <div class="flex flex-row items-start mb-3 -mt-1" v-if="rendering.tagline(item) && actual_size_mode >= CollectionItemSizeMode.MEDIUM">

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
        <div class="flex flex-row items-start">
          <img v-if="rendering.icon(item) && (!rendering.tagline(item) || actual_size_mode < CollectionItemSizeMode.MEDIUM)" :src="rendering.icon(item)" class="h-5 w-5 mr-2" />
          <button class="min-w-0 text-left text-[16px] font-['Lexend'] font-medium leading-tight break-words text-sky-700 hover:underline"
            v-html="rendering.title(item)"
            @click="appState.show_document_details([dataset_id, item_id], collection_item.metadata, collection_item.relevant_parts, original_query, /*in_new_tab*/ $event.metaKey)">
          </button>
          <div class="flex-1"></div>
          <span v-for="badge in rendering.badges(item)?.filter(badge => badge.applies)"
            v-tooltip.bottom="{ value: badge.tooltip, showDelay: 500 }"
            class="ml-2 px-2 py-[1px] rounded-xl bg-gray-200 text-xs text-gray-500">
            {{ badge.label }}
          </span>
          <button v-if="schema?.is_group_field && item[schema.is_group_field]"
            @click="collectionStore.show_group(item._dataset_id, item._id, `Directly in ${schema?.advanced_options?.group_name || 'Group'} '${rendering.title(item)}'`)"
            class="ml-2 px-2 py-[1px] rounded-xl bg-gray-100 text-xs text-gray-500 hover:bg-gray-200">
            {{ $t('CollectionItem.show-group-children', [schema?.advanced_options?.group_name || $t('CollectionItem.group-generic-name')]) }}
          </button>
        </div>

        <!-- Subtitle -->
        <p v-if="actual_size_mode >= CollectionItemSizeMode.MEDIUM"
          class="mt-0 text-[13px] break-words leading-normal text-gray-500"
          v-html="rendering.subtitle(item)"></p>

        <!-- Body -->
        <ExpandableTextArea class="mt-1"
          :html_content="rendering.body(item)" max_lines="3"
          v-if="actual_size_mode >= CollectionItemSizeMode.FULL" />

        <!-- Relevant Parts -->
        <RelevantPartsKeyword v-if="actual_size_mode >= CollectionItemSizeMode.FULL && !(schema?.is_group_field && item[schema.is_group_field])"
          :highlights="relevant_keyword_highlights"
          class="mt-2" :dataset_id="collection_item.dataset_id">
        </RelevantPartsKeyword>

        <RelevantPartsVector v-if="actual_size_mode >= CollectionItemSizeMode.FULL && !(schema?.is_group_field && item[schema.is_group_field])"
          :highlights="relevant_chunks"
          class="mt-2" :item="item || initial_item"
          :rendering="rendering">
        </RelevantPartsVector>

        <!-- Spacer if image on the right is larger than body -->
        <div class="flex-1"></div>
      </div>

      <!-- Right side (image) -->
      <div v-if="rendering.image(item) && actual_size_mode >= CollectionItemSizeMode.MEDIUM" class="flex-none w-24 flex flex-col justify-center">
        <Image class="w-full rounded-lg shadow-md" image-class="rounded-lg" :src="rendering.image(item)" preview />
      </div>
    </div>

    <!-- Footer -->
    <div class="flex flex-row gap-1 items-center">

        <div class="flex-1"></div>

        <span v-if="main_relevance_influence === 'vector'"
          v-tooltip.bottom="{ value: $t('CollectionItem.found-by-meaning-tooltip'), showDelay: 500 }"
          class="text-xs text-gray-400">
          {{ $t('CollectionItem.found-by-meaning') }}
        </span>
        <span v-if="main_relevance_influence === 'keyword'"
          v-tooltip.bottom="{ value: $t('CollectionItem.found-by-keywords-tooltip'), showDelay: 500 }"
          class="text-xs text-gray-400">
          {{ $t('CollectionItem.found-by-keywords') }}
        </span>
        <span v-if="main_relevance_influence === 'both'"
          v-tooltip.bottom="{ value: $t('CollectionItem.found-by-both-tooltip'), showDelay: 500 }"
          class="text-xs text-gray-400">
          {{ $t('CollectionItem.found-by-meaning-and-keywords') }}
        </span>

        <span class="italic px-2 text-xs text-gray-500">
          {{ appState.datasets[dataset_id]?.name }}
        </span>

        <div class="flex-1"></div>

        <div class="flex flex-row gap-1 items-center ring-orange-200 rounded"
          :class="{'ring-[1px]': is_candidate}">
          <div v-if="is_candidate" class="ml-1 mr-2 h-5 w-5 text-orange-400"
              v-tooltip.bottom="{value: $t('CollectionItem.temporary-item-explanation')}">
            <ArrowRightIcon class="w-full h-full">
            </ArrowRightIcon>
          </div>
          <BorderlessButton
            hover_color="hover:text-green-500" :highlight_color="collection_item.relevance >= ItemRelevance.APPROVED_BY_USER ? 'text-green-500' : 'text-orange-400'"
            :highlighted="collection_item.relevance > ItemRelevance.CANDIDATE" :default_padding="false" class="p-1"
            v-tooltip.bottom="{ value: $t('CollectionItem.add-this-item-permanently') }"
            @click="collectionStore.set_item_relevance(collection_item, 3)">
            <HandThumbUpIcon class="h-4 w-4"></HandThumbUpIcon>
          </BorderlessButton>
          <BorderlessButton
            hover_color="hover:text-red-500" :highlight_color="collection_item.relevance <= ItemRelevance.REJECTED_BY_USER ? 'text-red-500' : 'text-orange-400'"
            :highlighted="collection_item.relevance < ItemRelevance.CANDIDATE" :default_padding="false" class="p-1"
            v-tooltip.bottom="{ value: $t('CollectionItem.mark-this-item-as-irrelevant') }"
            @click="collectionStore.set_item_relevance(collection_item, -3)">
            <HandThumbDownIcon class="h-4 w-4"></HandThumbDownIcon>
          </BorderlessButton>
          <BorderlessButton v-if="show_remove_button"
            hover_color="hover:text-red-500" :default_padding="false" class="p-1"
            @click.stop="collectionStore.remove_item_from_collection([collection_item.dataset_id, collection_item.item_id], collection_item.collection, collection_item.classes.length ? collection_item.classes[0] : '_default')"
            v-tooltip.bottom="{ value: $t('CollectionItem.remove-from-this-collection'), showDelay: 400 }">
            <TrashIcon class="h-4 w-4"></TrashIcon>
          </BorderlessButton>
        </div>
      </div>

  </div>

  <!-- Alternative if rendering doesn't work to still be able to remove the item (e.g. if its deleted in the dataset) -->
  <div v-else>
    <button v-if="show_remove_button"
        @click.stop="collectionStore.remove_item_from_collection([collection_item.dataset_id, collection_item.item_id], collection_item.collection, collection_item.classes.length ? collection_item.classes[0] : '_default')"
        v-tooltip.right="{ value: $t('CollectionItem.remove-from-this-collection'), showDelay: 400 }"
        class="text-sm text-gray-400 hover:text-red-600">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
  </div>

</template>
