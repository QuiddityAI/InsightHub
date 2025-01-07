<script setup>

import {
  PlusIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import CollectionItem from "./CollectionItem.vue"
import BorderButton from "../widgets/BorderButton.vue";

import { CollectionItemSizeMode } from "../../utils/utils.js"

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
  props: ["collection_id", "class_name", "is_positive", "item_size_mode"],
  expose: [],
  emits: [],
  data() {
    return {
      selected_column: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collection() {
      return this.collectionStore.collection
    },
    active_search_sources() {
      return this.collectionStore.collection.search_sources.filter((source) => source.is_active)
    },
    retrieved_results() {
      return Math.max(this.active_search_sources.map((source) => source.retrieved))
    },
    available_results() {
      return Math.max(this.active_search_sources.map((source) => source.available))
    },
    any_source_is_estimated() {
      return this.active_search_sources.some((source) => !source.available_is_exact)
    },
    more_results_are_available() {
      return this.retrieved_results < this.available_results || this.any_source_is_estimated
    },
    is_last_page() {
      return (collectionStore.first_index + collectionStore.per_page) >= collectionStore.filtered_count
    },
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-row flex-wrap justify-center items-start gap-2 lg:gap-4" v-if="collection">

    <CollectionItem v-for="collection_item in collectionStore.collection_items"
      :dataset_id="collection_item.dataset_id"
      :item_id="collection_item.item_id"
      :initial_item="collection_item.metadata"
      :is_positive="collection_item.is_positive"
      :show_remove_button="true"
      :collection_item="collection_item"
      :size_mode="item_size_mode"
      @remove="collectionStore.remove_item_from_collection([collection_item.dataset_id, collection_item.item_id], collection_id, class_name)"
      :class="{
        'w-[320px]': item_size_mode <= CollectionItemSizeMode.SMALL,
        'w-[520px]': item_size_mode >= CollectionItemSizeMode.MEDIUM,
      }">

    </CollectionItem>

    <div v-if="collectionStore.search_mode && more_results_are_available && is_last_page"
      class="my-5 w-full flex flex-row justify-center">

      <BorderButton @click="collectionStore.add_items_from_active_sources"
        class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
        v-tooltip.top="{ value: `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''} results retrieved`}">
        Show More Results <PlusIcon class="h-4 w-4 inline"></PlusIcon>
      </BorderButton>
    </div>

  </div>
</template>

<style scoped>
</style>
