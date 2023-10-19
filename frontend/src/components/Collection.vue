<script setup>
import CollectionListItem from './CollectionListItem.vue';
</script>

<script>
export default {
  props: ["collection"],
  emits: ["remove_collection_item", "delete_item_collection",
          "recommend_items_for_collection", "show_collection_as_map"],
  data() {
    return {
    }
  },
  mounted() {
  },
}
</script>

<!-- TODO: run on server hotreload, check for-each, move methods or emit signals, forward remove item signal,
  add button to train concept, add threshold settings, add checkbox to mark results in map, add color / symbol select box,
  collaps list etc. -->

<template>

<li>
  <div class="flex flex-row gap-3">
    <span class="text-gray-500 font-medium">{{ collection.name }}</span>
    <div class="flex-1"></div>
    <button @click="delete_item_collection(collection.id)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Delete</button>
    <button @click="recommend_items_for_collection(collection)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Recommend Similar</button>
    <button @click="show_collection_as_map(collection)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
  </div>
  <ul class="pt-2">
    <li v-for="(item_id, index) in collection.positive_ids" :key="item_id" class="justify-between pb-2">
      <CollectionListItem :item_id="item_id" :schema_id="appState.settings.schema_id" :is-positive="true"
        @remove="collection.positives.splice(index, 1)" :rendering="collection_list_rendering">
      </CollectionListItem>
    </li>
  </ul>
  <ul class="pt-2">
    <li v-for="(item_id, index) in collection.negative_ids" :key="item_id" class="justify-between pb-2">
      <CollectionListItem :item_id="item_id" :schema_id="appState.settings.schema_id" :is-positive="false"
        @remove="collection.negatives.splice(index, 1)" :rendering="collection_list_rendering">
      </CollectionListItem>
    </li>
  </ul>
</li>

</template>


<style scoped></style>
