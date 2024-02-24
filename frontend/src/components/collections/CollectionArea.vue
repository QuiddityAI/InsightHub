<script setup>
import httpClient from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import CollectionList from "./CollectionList.vue"
import CollectionClassesList from "./CollectionClassesList.vue"
import CollectionClassDetails from "./CollectionClassDetails.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()

</script>

<script>
export default {
  props: [],
  emits: [],
  inject: ["eventBus"],
  data() {
    return {
      currently_selected_collection: null,
      currently_selected_collection_class: null,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on('collections_tab_is_clicked', () => {
      this.currently_selected_collection = null
      this.currently_selected_collection_class = null
    })
  },
  methods: {},
}
</script>

<template>
  <div>
    <CollectionList
      v-if="!currently_selected_collection && !currently_selected_collection_class"
      @collection_selected="(collection_id) => currently_selected_collection = collection_id"
      @class_selected="(class_name) => currently_selected_collection_class = class_name">
    </CollectionList>

    <CollectionClassesList
      v-if="currently_selected_collection && !currently_selected_collection_class"
      :collection_id="currently_selected_collection"
      @class_selected="(class_name) => currently_selected_collection_class = class_name"
      @close="currently_selected_collection = null">
    </CollectionClassesList>

    <CollectionClassDetails
      v-if="currently_selected_collection && currently_selected_collection_class"
      :collection_id="currently_selected_collection"
      :class_name="currently_selected_collection_class"
      @close="currently_selected_collection = null; currently_selected_collection_class = null">
    </CollectionClassDetails>
  </div>
</template>
