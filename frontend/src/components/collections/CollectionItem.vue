<script setup>
import {
  TrashIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
} from "@heroicons/vue/24/outline"

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
  props: ["dataset_id", "item_id", "initial_item", "is_positive", "show_remove_button", "collection_item"],
  emits: ["remove"],
  data() {
    return {
      item: {},
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    rendering() {
      return this.appStateStore.datasets[this.dataset_id]?.schema.result_list_rendering
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
      } else {
        this.get_full_item()
      }
    },
    get_full_item() {
      const that = this
      if (!this.dataset_id || !this.item_id) return
      const payload = {
        dataset_id: this.dataset_id,
        item_id: this.item_id,
        fields: this.rendering.required_fields,
      }
      httpClient.post("/data_backend/document/details_by_id", payload).then(function (response) {
        that.item = response.data
      })
    },
  },
}
</script>

<template>
  <div v-if="rendering && item" class="rounded bg-gray-100/50 p-3 flex flex-row gap-2">
    <div class="flex-1">
      <div class="flex flex-row">
        <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-5 w-5 mr-2" />
        <button class="text-left text-sm font-medium leading-tight hover:text-sky-600"
          v-html="rendering.title(item)"
          @click="appState.show_document_details([dataset_id, item_id])"
          >
        </button>
        <div class="flex-1"></div>
        <span v-if="collection_item.relevance >= -1 && collection_item.relevance <= 1"
          class="ml-2 text-xs text-orange-300">
          Candidate
        </span>
      </div>
      <p class="mt-1 text-xs leading-normal text-gray-500" v-html="rendering.subtitle(item)"></p>

      <div class="flex-1"></div>
      <div class="mt-2 flex flex-row gap-3 items-center">
        <span class="rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
          {{ appState.datasets[dataset_id]?.name }}
        </span>
        <div class="flex-1"></div>
        <button class="hover:text-green-500"
          :class="{ 'text-green-500': collection_item.relevance > 0 }"
          v-tooltip="{ value: 'Add this item permanently' }"
          @click="collectionStore.set_item_relevance(collection_item, 3)">
          <HandThumbUpIcon class="h-4 w-4"></HandThumbUpIcon>
        </button>
        <button class="hover:text-red-500"
          :class="{ 'text-red-500': collection_item.relevance < 0 }"
          v-tooltip="{ value: 'Mark this item as irrelevant, hide from future searches in this collection' }"
          @click="collectionStore.set_item_relevance(collection_item, -3)">
          <HandThumbDownIcon class="h-4 w-4"></HandThumbDownIcon>
        </button>
        <button v-if="show_remove_button"
          @click.stop="$emit('remove')"
          v-tooltip.right="{ value: 'Remove from this collection', showDelay: 400 }"
          class="text-sm text-gray-400 hover:text-red-600">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>
      </div>
    </div>
    <div v-if="rendering.image(item)" class="flex-none w-24 flex flex-col justify-center">
      <img class="w-full rounded-lg shadow-md" :src="rendering.image(item)" />
    </div>
  </div>
  <div v-else>
    <button v-if="show_remove_button"
        @click.stop="$emit('remove')"
        v-tooltip.right="{ value: 'Remove from this collection', showDelay: 400 }"
        class="text-sm text-gray-400 hover:text-red-600">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
  </div>
</template>
