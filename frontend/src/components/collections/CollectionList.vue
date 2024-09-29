<script setup>
import { httpClient } from "../../api/httpClient"

import {
  EllipsisVerticalIcon,
  TrashIcon,
  PlusIcon,
} from "@heroicons/vue/24/outline"

import CollectionClassListItem from "./CollectionClassListItem.vue"

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
  <div
    :class="{
      'w-[45px]': collapsed,
      'w-[230px]': !collapsed,
    }">

    <!-- Fix weird issue where panel doesn't take full width during transition -->
    <div class="bg-white h-[1px]"
      :class="{
        'w-[45px]': collapsed,
        'w-[230px]': !collapsed,
      }">
    </div>

    <div
      class="h-full overflow-y-auto flex flex-col gap-3 pt-5 pb-3 transition-width duration-300 shadow-md bg-white"
      :class="{
        'w-[45px]': collapsed,
        'w-[230px]': !collapsed,
      }">

      <div class="flex flex-row pb-2" :class="{ 'justify-center': collapsed }">
        <button
          @click="open_new_collection_dialog">
          <div v-if="collapsed"
            v-tooltip="{ value: 'Create a new collection', showDelay: 400 }"
            class="rounded-full h-7 w-7 bg-gray-200 flex flex-row items-center justify-center hover:bg-blue-100 hover:border hover:border-blue-200">
            <PlusIcon class="h-5 w-5"></PlusIcon>
          </div>
          <h3 v-else class="font-bold text-[15px] text-left pl-4">
            + New Collection
          </h3>
        </button>
      </div>

      <div v-for="collection in collectionStore.available_collections" :key="collection.id"
        class="flex flex-row" :class="{ 'justify-center': collapsed }">
        <button
          @click="collectionStore.open_collection(collection.id, collection.actual_classes[0].name)"
          :class="{'w-full': !collapsed}">
          <div v-if="collapsed"
            v-tooltip="{ value: collection.name, showDelay: 0 }"
            class="rounded-full h-7 w-7 text-gray-400 flex flex-row items-center justify-center hover:bg-blue-100 hover:border hover:border-blue-200"
            :class="{
              'bg-gray-100': !(collectionStore.collection_id == collection.id && collectionStore.class_name == collection.actual_classes[0].name),
              'bg-blue-100': collectionStore.collection_id == collection.id && collectionStore.class_name == collection.actual_classes[0].name,
              }">
            {{ collection.name.slice(0, 1) }}
          </div>
          <h3 v-else class="text-left text-[15px] text-md ml-3 mr-3 px-2 h-7 flex flex-row items-center rounded-md hover:text-blue-500 hover:bg-gray-100"
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
