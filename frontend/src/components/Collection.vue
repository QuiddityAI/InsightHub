<script setup>
import httpClient from '../api/httpClient';

import CollectionListItem from './CollectionListItem.vue';
import { mapStores } from 'pinia'
import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["collection"],
  emits: ["delete_item_collection", "recommend_items_for_collection", "show_collection_as_map"],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  methods: {
    remove_item_from_collection(item_id, is_positive) {
      const that = this
      const body = {
        collection_id: this.collection.id,
        item_id: item_id,
        is_positive: is_positive,
      }
      httpClient.post("/organization_backend/remove_item_from_collection", body)
        .then(function (response) {
          // 'collection' prop is read-only, so get writable reference:
          const collection_index = that.appStateStore.collections.findIndex((col) => col.id === that.collection.id)
          const collection = that.appStateStore.collections[collection_index]

          if (is_positive) {
            const item_index = collection.positive_ids.indexOf(item_id)
            collection.positive_ids.splice(item_index, 1)
          } else {
            const item_index = collection.negative_ids.indexOf(item_id)
            collection.negative_ids.splice(item_index, 1)
          }
        })
    },
  },
}
</script>

<!-- TODO: add button to train concept, add threshold settings, add checkbox to mark results in map, add color / symbol select box,
  collaps list etc. -->

<template>

<li>
  <div class="flex flex-row gap-3">
    <span class="text-gray-500 font-medium">{{ collection.name }}</span>
    <div class="flex-1"></div>
    <button @click="$emit('delete_item_collection', collection.id)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Delete</button>
    <button @click="$emit('recommend_items_for_collection', collection)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Recommend Similar</button>
    <button @click="$emit('show_collection_as_map', collection)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
  </div>
  <ul class="pt-2">
    <li v-for="(item_id, index) in collection.positive_ids" :key="item_id" class="justify-between pb-2">
      <CollectionListItem :item_id="item_id" :is_positive="true"
        @remove="remove_item_from_collection(item_id, true)">
      </CollectionListItem>
    </li>
  </ul>
  <ul class="pt-2">
    <li v-for="(item_id, index) in collection.negative_ids" :key="item_id" class="justify-between pb-2">
      <CollectionListItem :item_id="item_id" :is_positive="false"
        @remove="remove_item_from_collection(item_id, false)">
      </CollectionListItem>
    </li>
  </ul>
</li>

</template>


<style scoped></style>
