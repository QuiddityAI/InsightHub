<script setup>

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { FieldType, debounce } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      query: "",
      update_filter_debounced: debounce(() => {
        this.update_filter()
      }, 500),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
  },
  watch: {
    query() {
      this.update_filter_debounced()
    },
  },
  methods: {
    update_filter() {
      const filter_uid = `text_query`
      if (this.query.length === 0) {
        this.collectionStore.remove_filter(filter_uid)
      } else {
        const text_filter = {
          uid: filter_uid,
          display_name: `Contains: ${this.query}`,
          removable: false,
          filter_type: "text_query",
          value: this.query,
          field: '_descriptive_text_fields',
        }
        this.collectionStore.add_filter(text_filter)
      }
    },
  },
}
</script>

<template>
  <div class="flex-1 flex flex-row gap-1">
    <input v-model="query" type="text"
      class="ring-0 focus:ring-0 border border-gray-200 focus:border-blue-400 rounded-md px-2 py-0 w-full"
      :placeholder="$t('TextFilterInput.text-filter-placeholder')" />
  </div>
</template>

<style scoped>
</style>
