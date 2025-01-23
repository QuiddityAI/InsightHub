<script setup>
import ProgressSpinner from 'primevue/progressspinner';

import VueWordCloud from 'vuewordcloud';

import { debounce } from '../../utils/utils';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from '../../stores/map_state_store';
import { useCollectionStore } from '../../stores/collection_store';

const appState = useAppStateStore()
const mapStateStore = useMapStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      fetch_important_words_debounced: debounce(() => {
        let item_ids = this.mapStateStore.selected_collection_item_ids
        if (item_ids.length === 0) {
          item_ids = this.collectionStore.filtered_item_ids
        }
        this.collectionStore.fetch_important_words(item_ids)
      }, 500),
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.fetch_important_words_debounced()
    this.eventBus.on("collection_filters_changed", this.fetch_important_words_debounced)
  },
  unmounted() {
    this.eventBus.off("collection_filters_changed", this.fetch_important_words_debounced)
  },
  watch: {
    "mapStateStore.selected_collection_item_ids"() {
      this.fetch_important_words_debounced()
    },
  },
  methods: {
    add_word_filter(text) {
      const filter_uid = `word_cloud_filter`
      const text_filter = {
        uid: filter_uid,
        display_name: `Contains: ${text}`,
        removable: true,
        filter_type: "text_query",
        value: text,
        field: '_descriptive_text_fields',
      }
      this.collectionStore.add_filter(text_filter)
    },
  },
}
</script>

<template>
  <div
    class="mt-3 py-2 px-3 text-sm text-gray-500 rounded-md bg-gray-100/50">
    <b>Important keywords in filtered / selected items:</b>
    <ProgressSpinner class="ml-2 w-4 h-4" v-if="collectionStore.important_words_are_loading" />
    <br>
    <VueWordCloud :words="collectionStore.important_words"
      font-family="Lexend"
      color="Gray"
      :spacing="0.9"
      style="width: 100%; height: 125px;">
      <template v-slot="props">
        <button
          class="px-1 text-gray-500 rounded-md hover:bg-gray-100"
          @click="add_word_filter(props.text)">
          {{ props.text }}
        </button>
      </template>
    </VueWordCloud>
  </div>
</template>

<style scoped>
</style>
