<script setup>
import {
  TrashIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
} from "@heroicons/vue/24/outline"

import BorderlessButton from "../widgets/BorderlessButton.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
import { httpClient } from "../../api/httpClient"
import { useCollectionStore } from "../../stores/collection_store";

export default {
  props: ["dataset_id", "item_id", "initial_item", "is_positive", "show_remove_button", "collection_item", "size_mode"],
  emits: ["remove"],
  data() {
    return {
      item: {},
      loading_item: false,
      body_text_collapsed: true,
      show_more_button: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    rendering() {
      return this.appStateStore.datasets[this.dataset_id]?.schema.result_list_rendering
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
    actual_size_mode() {
      if (this.is_irrelevant_according_to_ai) {
        return "small"
      }
      return this.size_mode || "full"
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
      if (!this.dataset_id || !this.item_id) return
      const payload = {
        dataset_id: this.dataset_id,
        item_id: this.item_id,
        fields: this.rendering.required_fields,
      }
      that.loading_item = true
      httpClient.post("/data_backend/document/details_by_id", payload).then(function (response) {
        that.item = { ...that.item, ...response.data }
          // height of text is only available after rendering:
          setTimeout(() => {
            that.show_more_button = that.$refs.body_text?.scrollHeight > that.$refs.body_text?.clientHeight
          }, 100)
          that.loading_item = false
      })
    },
  },
}
</script>

<template>
  <div v-if="rendering && item && collection_item"
    class="flex flex-col gap-3 pb-2 pt-4 pl-4 pr-4 mb-2 rounded-md bg-white shadow-md"
    :class="{'opacity-60': is_irrelevant_according_to_ai}">

    <div class="flex flex-row">

      <!-- Left side (content, not image) -->
      <div class="flex-1 flex flex-col gap-1">

        <!-- Heading -->
        <div class="flex flex-row items-start">
          <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-5 w-5 mr-2" />
          <button class="text-left text-[15px] font-serif font-bold leading-tight text-sky-700 hover:underline"
            v-html="rendering.title(item)"
            @click="appState.show_document_details([dataset_id, item_id])">
          </button>
          <div class="flex-1"></div>
          <span v-if="collection_item.relevance >= -1 && collection_item.relevance <= 1"
            class="ml-2 text-xs text-orange-300">
            Candidate
          </span>
          <span v-for="tag in rendering.tags(item)?.filter(tag => tag.applies)"
            v-tooltip.bottom="{ value: tag.tooltip, showDelay: 500 }"
            class="ml-2 px-2 py-[1px] rounded-xl bg-gray-200 text-xs text-gray-500">
            {{ tag.label }}
          </span>
        </div>

        <!-- Subtitle -->
        <p class="mt-1 text-xs leading-normal text-gray-500" v-html="rendering.subtitle(item)"></p>

        <!-- Body -->
        <p ref="body_text" v-if="actual_size_mode === 'full'"
          class="mt-1 text-[13px] text-gray-700" :class="{ 'line-clamp-[6]': body_text_collapsed }"
        v-html="rendering.body(item)"></p>

        <!-- Sapcer if image on the right is larger than body -->
        <div class="flex-1"></div>
      </div>

      <!-- Right side (image) -->
      <div v-if="rendering.image(item)" class="flex-none w-24 flex flex-col justify-center">
        <img class="w-full rounded-lg shadow-md" :src="rendering.image(item)" />
      </div>
    </div>

    <!-- Footer -->
    <div class="flex flex-row gap-1 items-center">
        <div v-if="show_more_button && actual_size_mode === 'full'" class="text-xs text-gray-700">
          <button @click.prevent="body_text_collapsed = !body_text_collapsed" class="text-gray-500">
            {{ body_text_collapsed ? "Show more" : "Show less" }}
          </button>
        </div>

        <div class="flex-1"></div>

        <span v-if="main_relevance_influence === 'vector'"
          v-tooltip.bottom="{ value: 'This item was mainly found because it matches the meaning of the search query.', showDelay: 500 }"
          class="text-xs text-gray-400">
          Found by Meaning
        </span>
        <span v-if="main_relevance_influence === 'keyword'"
          v-tooltip.bottom="{ value: 'This item was mainly found because it contains keywords of the search query.', showDelay: 500 }"
          class="text-xs text-gray-400">
          Found by Keywords
        </span>
        <span v-if="main_relevance_influence === 'both'"
          v-tooltip.bottom="{ value: 'This item was found by meaning and keywords.', showDelay: 500 }"
          class="text-xs text-gray-400">
          Found by Meaning & Keywords
        </span>

        <span class="italic px-2 text-xs text-gray-500">
          {{ appState.datasets[dataset_id]?.name }}
        </span>

        <div class="flex-1"></div>

        <BorderlessButton
          hover_color="hover:text-green-500" highlight_color="text-green-500"
          :highlighted="collection_item.relevance > 0" :default_padding="false" class="p-1"
          v-tooltip="{ value: 'Add this item permanently' }"
          @click="collectionStore.set_item_relevance(collection_item, 3)">
          <HandThumbUpIcon class="h-4 w-4"></HandThumbUpIcon>
        </BorderlessButton>
        <BorderlessButton
          hover_color="hover:text-red-500" highlight_color="text-red-500"
          :highlighted="collection_item.relevance < 0" :default_padding="false" class="p-1"
          v-tooltip="{ value: 'Mark this item as irrelevant, hide from future searches in this collection' }"
          @click="collectionStore.set_item_relevance(collection_item, -3)">
          <HandThumbDownIcon class="h-4 w-4"></HandThumbDownIcon>
        </BorderlessButton>
        <BorderlessButton v-if="show_remove_button"
          hover_color="hover:text-red-500" :default_padding="false" class="p-1"
          @click.stop="$emit('remove')"
          v-tooltip.right="{ value: 'Remove from this collection', showDelay: 400 }">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </BorderlessButton>
      </div>

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
