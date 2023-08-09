<script setup>

import { Disclosure, DisclosureButton, DisclosurePanel, Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { Bars3Icon, BellIcon, XMarkIcon } from '@heroicons/vue/24/outline'

import SearchAndMap from './SearchAndMap.vue';
import SearchAndMapAbsclust from './SearchAndMapAbsclust.vue';
</script>

<script>

export default {
  data() {
    return {
      userNavigation: [
        { name: 'Your Profile', href: '#' },
        { name: 'Settings', href: '#' },
        { name: 'Sign out', href: '#' },
      ],
      navigation: [
        { name: 'Search & Map', href: '#', current: true },
        { name: 'Lists', href: '#', current: false },
      ],
      user: {
        name: 'Tom Cook',
        email: 'tom@example.com',
        imageUrl:
          'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80',
      },
      urlHashPart: window.location.hash,
    }
  },
  methods: {

  }
}

</script>

<template>
  <div class="min-h-full">
    <SearchAndMap v-if="urlHashPart !== '#absclust'"/>
    <SearchAndMapAbsclust v-if="urlHashPart === '#absclust'"/>
  </div>
</template>

<style scoped></style>
