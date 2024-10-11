<script setup>

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
export default {
  props: [],
  emits: [],
  data() {
    return {}
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collapsed() {
      return this.collectionStore.collection_id !== null
    },
  },
  mounted() {},
  methods: {
    open_new_collection_dialog() {
      this.collectionStore.close_collection()
    },
  },
}
</script>

<template>
  <div class="h-full w-[250px] transition-[margin] duration-300"
    :class="{
      '-ml-[250px]': collapsed,
      'ml-0': !collapsed,
    }">

    <div
      class="h-full overflow-y-auto flex flex-col gap-3 pt-6 pb-3 shadow-md bg-white">

      <div class="ml-5 flex flex-row items-center text-left">
        <h3 class="font-bold text-[15px]">
          Recent Collections
        </h3>
      </div>

      <div v-for="collection in collectionStore.available_collections" :key="collection.id"
        class="flex flex-row">
        <button
          @click="collectionStore.open_collection(collection.id, collection.actual_classes[0].name)">
          <h3 class="text-left text-[15px] text-md ml-3 mr-3 px-2 py-1 flex flex-row items-center rounded-md hover:text-blue-500 hover:bg-gray-100"
            :class="{
              'text-blue-500': collectionStore.collection_id == collection.id && collectionStore.class_name == collection.actual_classes[0].name,
              }">
            {{ collection.name }}
          </h3>
        </button>
      </div>

    </div>
  </div>
</template>
